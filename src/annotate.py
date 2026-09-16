"""Consenso de tres anotadores independientes por llamada.

La extracción original es una sola pasada de un solo modelo. Para no depender de ella,
cada transcripción la anotan tres agentes, sin ver lo que respondieron los otros ni la
extracción original, y cada celda se queda con la respuesta de al menos dos de tres. Si
no hay mayoría, la celda queda vacía y marcada. La extracción solo vuelve a entrar en la
regla literal de fecha, como fuente de citas que tienen que existir en la transcripción.

  clasificador   Sonnet   aplica la rúbrica
  auditor        Opus     aplica la rúbrica
  reauditor      Opus     aplica la rúbrica exigiendo cada criterio al pie de la letra

Los tres son agentes internos de Claude Code orquestados por un workflow, con las
instrucciones de docs/panel-de-anotacion.md. Este módulo no llama a ningún modelo: guarda
sus respuestas, vota y mide el acuerdo. Cuando existe la segunda transcripción
(large-v3), cada agente lee las dos.

Lo que esto mide y lo que no: tres anotadores de acuerdo miden consistencia, no verdad.
Comparten la rúbrica y parte de sus sesgos, así que el acuerdo no sustituye escuchar. Lo
que sí hace es separar las celdas firmes (3 de 3) de las frágiles (2 de 3 o sin mayoría).
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from itertools import combinations
from pathlib import Path

from src.anchoring import is_anchored, transcripts_seen
from src.extract import SCHEMA, call_id, clean

ROOT = Path(__file__).resolve().parent.parent
INTERIM = ROOT / "data" / "interim"
TRANSCRIPTS = INTERIM / "transcripts"
SECOND = INTERIM / "transcripts_large-v3"
PANEL_INPUT = INTERIM / "panel_input"
ANNOTATIONS = INTERIM / "annotations"
CONSENSUS = INTERIM / "consensus"

# Las cuatro conductas que el informe rotula como alertas de cumplimiento.
ALERTAS = (
    "legal_department_framing",
    "offer_expiry_claim",
    "situational_legal_pressure",
    "credit_benefit_promised",
)
LISTENING = INTERIM / "escucha_compromisos.json"
EXTRACTIONS = INTERIM / "extractions"
PUBLIC = ROOT / "data" / "public"

PANEL = {"clasificador": "sonnet", "auditor": "opus", "reauditor": "opus"}

# La rúbrica cuenta «hoy» como fecha resoluble en la propuesta con cifras (src/rubric.md,
# variable 10). El panel no la aceptó cuando la fecha era el vencimiento de la oferta
# («vencería hoy mismo»). La regla escrita se aplica después del voto, sin volver a anotar.
LITERAL_DATE_FIELD = "quantified_proposal_stated"
COMMITMENT_FIELD = "qualified_payment_commitment"
AMOUNT = re.compile(r"\d|\bmil\b|\bmill[oó]n", re.I)
TODAY = re.compile(r"\bhoy\b", re.I)


def fields() -> list[str]:
    return [
        key
        for key in json.loads(SCHEMA.read_text(encoding="utf-8"))["properties"]
        if key != "call_id"
    ]


def _readable_second(path: Path) -> str | None:
    """La segunda transcripción ya limpia, o None si aún no existe o se está escribiendo.

    stage() se puede correr mientras large-v3 sigue transcribiendo: un JSON a medio
    escribir se trata como si todavía no estuviera.
    """
    if not path.exists():
        return None
    try:
        return clean(json.loads(path.read_text(encoding="utf-8"))["transcription"])
    except (json.JSONDecodeError, KeyError):
        return None


def stage() -> dict:
    """Copia las transcripciones a carpetas sin el brazo en la ruta, ya limpias.

    Los agentes leen de data/interim/panel_input/<uuid>/, así que no ven si la llamada
    viene de humano/ o de ia/. Se aplica la misma limpieza que usó la extracción original
    (alucinaciones de YouTube y bucles del decodificador). Re-ejecutable: añade la segunda
    transcripción cuando aparece.
    """
    staged, with_second = 0, 0
    for arm in ("humano", "ia"):
        for path in sorted((TRANSCRIPTS / arm).glob("*.json")):
            folder = PANEL_INPUT / path.stem
            folder.mkdir(parents=True, exist_ok=True)
            first = json.loads(path.read_text(encoding="utf-8"))["transcription"]
            (folder / "transcripcion_a.txt").write_text(clean(first), encoding="utf-8")
            text = _readable_second(SECOND / arm / path.name)
            if text is not None:
                (folder / "transcripcion_b.txt").write_text(text, encoding="utf-8")
                with_second += 1
            staged += 1
    return {"llamadas": staged, "con_segunda_transcripcion": with_second}


def persist(annotations: list[dict], root: Path = ANNOTATIONS) -> int:
    """Guarda las respuestas del workflow, una por rol y llamada.

    El identificador no se toma del agente —los modelos devuelven un marcador de
    posición—, sino que se deriva del nombre del archivo, igual que en el inventario.
    """
    for item in annotations:
        row = dict(item["anotacion"])
        row.update(
            call_id=call_id(item["stem"]), arm=item["arm"], _rol=item["rol"], _modelo=item["modelo"]
        )
        target = root / item["rol"] / item["arm"] / f"{item['stem']}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(annotations)


def _value(cell):
    return cell.get("value") if isinstance(cell, dict) else cell


def vote(rows: list[dict], names: list[str]) -> dict:
    """Celda a celda: la respuesta de al menos dos anotadores, o vacía si no hay mayoría."""
    consensus = {"call_id": rows[0]["call_id"], "arm": rows[0]["arm"], "_acuerdo": {}}
    for name in names:
        answers = [json.dumps(_value(row.get(name)), sort_keys=True) for row in rows]
        winner, count = Counter(answers).most_common(1)[0]
        if count >= 2:
            consensus[name] = next(
                r[name] for r, a in zip(rows, answers, strict=True) if a == winner
            )
        else:
            consensus[name] = {"value": None}
        consensus["_acuerdo"][name] = f"{count}/{len(rows)}"
    return consensus


def apply_literal_date_rule(consensus: dict, sources: list[dict], transcripts: list[str]) -> bool:
    """Aplica la regla literal de fecha a la propuesta con cifras. Devuelve si cambió la celda.

    Si la celda no quedó en True pero alguna anotación de la llamada —del panel o de la
    extracción original— la marcó True con una cita que tiene un monto y «hoy», y esa cita
    existe en la transcripción, la celda pasa a True con ella. Una cita que no ancla no
    basta para contradecir al panel. La regla es simétrica entre brazos.
    """
    if _value(consensus.get(LITERAL_DATE_FIELD)) is True:
        return False
    for source in sources:
        candidate = source.get(LITERAL_DATE_FIELD)
        quote = candidate.get("quote") if isinstance(candidate, dict) else None
        if not (
            _value(candidate) is True and quote and AMOUNT.search(quote) and TODAY.search(quote)
        ):
            continue
        if any(is_anchored(quote, text) for text in transcripts):
            consensus[LITERAL_DATE_FIELD] = {"value": True, "quote": quote}
            consensus.setdefault("_ajustes", {})[LITERAL_DATE_FIELD] = (
                "regla literal: «hoy» es fecha"
            )
            return True
    return False


def listening() -> dict:
    """Lo que el analista oyó en las celdas de compromiso que el panel no resolvió.

    Las 14 celdas sin unanimidad se escucharon una a una (docs/decisiones.md §17). El oído humano
    manda sobre el voto de los modelos en esas celdas y solo en esas: es la única validación
    externa del KPI comercial. El archivo no se versiona porque se indexa por llamada.
    """
    if not LISTENING.exists():
        return {}
    return json.loads(LISTENING.read_text(encoding="utf-8"))


def publish_listening(heard: dict) -> int:
    """Publica el rastro auditable de la escucha, sin una palabra de las llamadas.

    Desde un clon, la única validación externa del KPI comercial era una caja negra: el
    archivo que la registra se indexa por nombre de audio y lleva notas con montos de
    llamadas concretas, así que no se versiona. Lo que sí se puede publicar —y hace falta
    para cotejar— es qué celda se escuchó, qué había votado el panel y qué se oyó. El
    identificador es el mismo hash del nombre del archivo que usa todo `data/public/`.
    """
    rows = [
        {
            "call_id": call_id(key.split("/", 1)[1]),
            "arm": key.split("/", 1)[0],
            "panel": item["panel"],
            "escuchado": item["valor"],
        }
        for key, item in sorted(heard.items())
    ]
    (PUBLIC / "escucha_compromisos.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return len(rows)


def apply_listening(consensus: dict, arm: str, stem: str, heard: dict) -> bool:
    """Reemplaza el compromiso votado por lo que se oyó. Devuelve si cambió el nivel."""
    item = heard.get(f"{arm}/{stem}")
    if item is None:
        return False
    cell = consensus.get(COMMITMENT_FIELD) or {}
    before = _value(cell)
    consensus[COMMITMENT_FIELD] = {
        "value": item["valor"],
        "quote_terms": cell.get("quote_terms"),
        "quote_acceptance": cell.get("quote_acceptance"),
    }
    consensus.setdefault("_ajustes", {})[COMMITMENT_FIELD] = "escucha del analista"
    return before != item["valor"]


def pair_agreement() -> dict:
    """Cuánta independencia tiene de verdad un panel de tres, medida y no supuesta.

    «Vale la mayoría» suena a tres opiniones. Dos de los tres anotadores son de la misma
    familia de modelos, y la literatura de paneles de jueces dice que los errores entre
    modelos están correlacionados —más cuanto mejores son—, así que el voto puede valer
    menos de lo que su número sugiere.

    Lo que se puede medir sin etiquetas de oro es el acuerdo por pares. El número que
    importa no es el global —con una tasa base tan baja, todos coinciden en los «no»— sino
    **el acuerdo dentro de las celdas donde el panel se partió**: ahí se ve quién decide.
    """
    names = fields()
    votes: dict[tuple, dict[str, str]] = {}
    for rol in PANEL:
        for path in (ANNOTATIONS / rol).glob("*/*.json"):
            row = json.loads(path.read_text(encoding="utf-8"))
            for name in names:
                cell = votes.setdefault((path.parent.name, path.stem, name), {})
                cell[rol] = json.dumps(_value(row.get(name)), sort_keys=True)
    split = [v for v in votes.values() if len(set(v.values())) > 1]
    pares = {}
    for a, b in combinations(PANEL, 2):
        juntos = sum(1 for v in split if v.get(a) == v.get(b))
        pares[f"{a}|{b}"] = {
            "acuerdo_total": sum(1 for v in votes.values() if v.get(a) == v.get(b)),
            "acuerdo_en_disputadas": juntos,
        }
    return {"celdas": len(votes), "disputadas": len(split), "pares": pares}


def script_concentration() -> dict:
    """Cuánto de cada conducta marcada es una sola frase de guion repetida.

    Cambia lo que se puede recomendar. Si los 21 positivos de una conducta comparten la misma
    oración, no hay un problema de comportamiento: hay una línea de guion, y se corrige
    editándola. Si son veintidós formulaciones distintas, es formación y supervisión, que es
    otro presupuesto y otro plazo.

    Se mide sobre el fragmento de seis palabras más repetido entre las citas ancladas. Se
    publica solo la proporción, nunca el texto: el archivo es público y esto se calcula sobre
    transcripciones que no salen de `data/interim/`.
    """
    out: dict[str, dict[str, dict[str, int]]] = {}
    for name in ALERTAS:
        for arm in ("ia", "humano"):
            quotes = []
            for path in (CONSENSUS / arm).glob("*.json"):
                row = json.loads(path.read_text(encoding="utf-8"))
                cell = row.get(name) or {}
                if not (isinstance(cell, dict) and _value(cell)):
                    continue
                text = " ".join(str(v) for k, v in cell.items() if k.startswith("quote") and v)
                quotes.append(re.sub(r"[^a-záéíóúñü ]", "", text.lower()).split())
            if not quotes:
                continue
            counts: Counter = Counter()
            for words in quotes:
                for i in range(max(1, len(words) - 5)):
                    counts[" ".join(words[i : i + 6])] += 1
            comparten = counts.most_common(1)[0][1] if counts else 0
            out.setdefault(name, {})[arm] = {
                "positivos": len(quotes),
                "comparten_la_misma_frase": min(comparten, len(quotes)),
            }
    return out


def consolidate() -> dict:
    """Vota cada llamada con las anotaciones disponibles y escribe su consenso."""
    names = fields()
    calls = {(p.parent.name, p.stem) for p in ANNOTATIONS.glob("*/*/*.json")}
    agreement, complete, partial = Counter(), 0, 0
    adjusted = Counter()
    heard = listening()
    if heard:
        publish_listening(heard)
    reheard = Counter()
    for arm, stem in sorted(calls):
        rows = [
            json.loads(path.read_text(encoding="utf-8"))
            for role in PANEL
            if (path := ANNOTATIONS / role / arm / f"{stem}.json").exists()
        ]
        if len(rows) < 2:
            continue
        complete += len(rows) == len(PANEL)
        partial += len(rows) < len(PANEL)
        consensus = vote(rows, names)
        original = EXTRACTIONS / arm / f"{stem}.json"
        extra = [json.loads(original.read_text(encoding="utf-8"))] if original.exists() else []
        texts = transcripts_seen(arm, stem, CONSENSUS)
        adjusted[arm] += apply_literal_date_rule(consensus, rows + extra, texts)
        reheard[arm] += apply_listening(consensus, arm, stem, heard)
        target = CONSENSUS / arm / f"{stem}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(consensus, ensure_ascii=False, indent=2), encoding="utf-8")
        agreement.update(consensus["_acuerdo"].values())
    return {
        "llamadas_con_tres_votos": complete,
        "llamadas_con_dos_votos": partial,
        "celdas": dict(agreement),
        "ajustes_regla_literal": dict(adjusted),
        "celdas_escuchadas": len(heard),
        "cambios_por_escucha": dict(reheard),
    }


def agreement_with_extraction(names: list[str]) -> dict:
    """Cuánto coincide la extracción original, de un solo modelo, con el consenso del panel.

    Si la mayoría de tres anotadores contradice a la extracción en una variable, esa
    variable no era firme. Solo conteos, ni una palabra de las llamadas.
    """
    table = {name: {"coinciden": 0, "total": 0} for name in names}
    for path in sorted(CONSENSUS.glob("*/*.json")):
        original = EXTRACTIONS / path.parent.name / path.name
        if not original.exists():
            continue
        consensus = json.loads(path.read_text(encoding="utf-8"))
        first = json.loads(original.read_text(encoding="utf-8"))
        for name in names:
            table[name]["total"] += 1
            table[name]["coinciden"] += _value(consensus.get(name)) == _value(first.get(name))
    return table


def family_positives() -> dict:
    """Positivos de cada variable de la familia por brazo, en la extracción y en el consenso.

    Es lo que permite decir en el informe cuánto cambió una cifra al pasar de un modelo a
    tres, leyendo el número en vez de escribirlo.
    """
    from src.analyze import FAMILY, cell

    counts = {}
    for name, _, _ in FAMILY:
        counts[name] = {}
        for label, root in (("extraccion", EXTRACTIONS), ("consenso", CONSENSUS)):
            counts[name][label] = {
                arm: sum(
                    cell(json.loads(p.read_text(encoding="utf-8")), name)
                    for p in sorted((root / arm).glob("*.json"))
                )
                for arm in ("humano", "ia")
            }
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Consenso del panel de anotadores.")
    parser.add_argument(
        "--stage", action="store_true", help="prepara las carpetas ciegas para los agentes"
    )
    parser.add_argument("--from-workflow", type=Path, help="salida JSON del workflow de anotación")
    args = parser.parse_args()

    if args.stage:
        staged = stage()
        if not staged["llamadas"]:
            raise SystemExit(
                "No hay transcripciones en data/interim/transcripts. Corre `make transcribe`."
            )
        print(json.dumps(staged, ensure_ascii=False))
        return

    if args.from_workflow:
        if not args.from_workflow.exists():
            raise SystemExit(f"No existe la salida del workflow: {args.from_workflow}")
        payload = json.loads(args.from_workflow.read_text(encoding="utf-8"))
        result = payload.get("result", payload)
        print(f"Guardadas {persist(result['anotaciones'])} anotaciones")

    summary = consolidate()
    if not summary["llamadas_con_tres_votos"] + summary["llamadas_con_dos_votos"]:
        raise SystemExit(
            "No hay anotaciones del panel en data/interim/annotations: nada que votar. "
            "Ver docs/panel-de-anotacion.md."
        )
    agreement = agreement_with_extraction(fields())
    PUBLIC.mkdir(parents=True, exist_ok=True)
    (PUBLIC / "agreement.json").write_text(
        json.dumps(
            {
                "panel": PANEL,
                "resumen": summary,
                "acuerdo_por_pares": pair_agreement(),
                "concentracion_guion": script_concentration(),
                "extraccion_vs_consenso": agreement,
                "positivos_familia": family_positives(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False))
    for name, counts in agreement.items():
        print(f"  {name:<30} extracción = consenso en {counts['coinciden']}/{counts['total']}")


if __name__ == "__main__":
    main()
