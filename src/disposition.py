"""Desenlace de la llamada y reacción del interlocutor: consenso, anclaje y análisis exploratorio.

La rúbrica (src/rubric_desenlace.md) y los cortes (docs/hipotesis.md §7) se congelaron antes de
anotar. Anota el mismo panel de tres agentes ciegos que la familia de 8, con voto 2 de 3 y citas
que se verifican en la transcripción. Nada de esto entra a la familia: es exploratorio, sin
Westfall-Young, con IC de Newcombe por brazo, en el total y dentro de las gestiones nuevas.

  uv run python -m src.disposition --from-workflow <salida>   guarda, vota, ancla y analiza
  uv run python -m src.disposition                             rehace consenso y análisis
  uv run python -m src.disposition --listening-sheet           hoja de escucha de 20 llamadas
  uv run python -m src.disposition --agreement <hoja llena>    acuerdo del oído con el panel
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path

import numpy as np

from src.analyze import CONSENSUS as FAMILY_CONSENSUS
from src.analyze import cell
from src.anchoring import is_anchored, transcripts_seen
from src.annotate import PANEL, persist, vote
from src.stats import compare_proportions

ROOT = Path(__file__).resolve().parent.parent
INTERIM = ROOT / "data" / "interim"
ANNOTATIONS = INTERIM / "annotations_desenlace"
CONSENSUS = INTERIM / "consensus_desenlace"
PUBLIC = ROOT / "data" / "public"
SCHEMA = ROOT / "src" / "schema_desenlace.json"
INVENTORY = INTERIM / "inventory.csv"
SHEET = INTERIM / "hoja_escucha_desenlace.csv"
SHEET_KEY = INTERIM / "hoja_escucha_desenlace_clave.csv"

ARMS = ("ia", "humano")
POSITIVE = {"acepta_parcial", "acepta_total", "acepta_alcance_indeterminado"}
BROAD = POSITIVE | {"acepta_vago"}
DISTRESS = {"angustiado", "molesto"}
NOT_EVALUABLE = {None, "no_aplica"}
MIN_DENOMINATOR = 20  # por debajo, solo conteos (docs/hipotesis.md §7)
LISTEN_PER_ARM = 10
LISTEN_SECONDS = 90
SEED = 20260914


def fields() -> list[str]:
    properties = json.loads(SCHEMA.read_text(encoding="utf-8"))["properties"]
    return [key for key in properties if key != "call_id"]


def value(row: dict, key: str):
    cell_value = row.get(key)
    return cell_value.get("value") if isinstance(cell_value, dict) else cell_value


def consolidate() -> dict:
    """Vota cada llamada anotada por el panel y escribe su consenso."""
    names = fields()
    calls = {(p.parent.name, p.stem) for p in ANNOTATIONS.glob("*/*/*.json")}
    agreement = {name: Counter() for name in names}
    for arm, stem in sorted(calls):
        rows = [
            json.loads(path.read_text(encoding="utf-8"))
            for role in PANEL
            if (path := ANNOTATIONS / role / arm / f"{stem}.json").exists()
        ]
        if len(rows) < 2:
            continue
        consensus = vote(rows, names)
        target = CONSENSUS / arm / f"{stem}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(consensus, ensure_ascii=False, indent=2), encoding="utf-8")
        for name in names:
            agreement[name][consensus["_acuerdo"][name]] += 1
    return {name: dict(counts) for name, counts in agreement.items()}


def load() -> list[dict]:
    """Consenso de desenlace unido al tipo de gestión y al compromiso de la familia."""
    rows = []
    for arm in ARMS:
        for path in sorted((CONSENSUS / arm).glob("*.json")):
            row = json.loads(path.read_text(encoding="utf-8"))
            family = json.loads((FAMILY_CONSENSUS / arm / path.name).read_text(encoding="utf-8"))
            row["_stem"] = path.stem
            row["_new_case"] = not bool(value(family, "prior_agreement_followup"))
            row["_qualified_commitment"] = cell(family, "qualified_payment_commitment")
            rows.append(row)
    if not rows:
        raise SystemExit(
            "No hay consenso de desenlace en data/interim/consensus_desenlace. "
            "Corre el panel con src/rubric_desenlace.md y luego --from-workflow."
        )
    return rows


def anchoring(rows: list[dict]) -> dict:
    """Respuestas con contenido cuya cita existe en las transcripciones que vio el panel."""
    counts = {name: {arm: {"con_valor": 0, "anclados": 0} for arm in ARMS} for name in fields()}
    for row in rows:
        texts = transcripts_seen(row["arm"], row["_stem"], FAMILY_CONSENSUS)
        for name in fields():
            if value(row, name) in (None, False, "no_aplica"):
                continue
            quotes = [q for k, q in row[name].items() if k.startswith("quote") and q]
            bucket = counts[name][row["arm"]]
            bucket["con_valor"] += 1
            bucket["anclados"] += bool(quotes) and all(
                any(is_anchored(q, text) for text in texts) for q in quotes
            )
    return counts


def _cut(rows: list[dict], name: str, hits: set, denominator: set | None) -> dict:
    """Tasa de un corte por brazo, con su contraste IA − humano."""
    counts = {}
    for arm in ARMS:
        members = [r for r in rows if r["arm"] == arm]
        if denominator is not None:
            members = [r for r in members if value(r, name) in denominator]
        counts[arm] = (sum(value(r, name) in hits for r in members), len(members))
    (k_ai, n_ai), (k_human, n_human) = counts["ia"], counts["humano"]
    out = {"k_ia": k_ai, "n_ia": n_ai, "k_humano": k_human, "n_humano": n_human}
    if min(n_ai, n_human) >= MIN_DENOMINATOR:
        test = compare_proportions(k_ai, n_ai, k_human, n_human)
        out.update(
            diff_pp=test.diff_pp,
            ci_low_pp=test.ci_low_pp,
            ci_high_pp=test.ci_high_pp,
            p_fisher=test.p_value,
        )
    return out


def cuts(rows: list[dict]) -> dict:
    """Los cortes pre-registrados en docs/hipotesis.md §7."""
    evaluable = {
        v
        for v in json.loads(SCHEMA.read_text(encoding="utf-8"))["properties"]["final_disposition"][
            "properties"
        ]["value"]["enum"]
    } - NOT_EVALUABLE
    difficulty = {
        "reconoce_y_ofrece",
        "ofrece_sin_reconocer",
        "reconoce_sin_ofrecer",
        "insiste_o_presiona",
    }
    states = {"cooperativo", "angustiado", "molesto", "evasivo"}
    return {
        "positivo": _cut(rows, "final_disposition", POSITIVE, evaluable),
        "positivo_amplio": _cut(rows, "final_disposition", BROAD, evaluable),
        "positivo_por_llamada": _cut(rows, "final_disposition", POSITIVE, None),
        "peso_parcial": _cut(rows, "final_disposition", {"acepta_parcial"}, POSITIVE),
        "malestar_al_cierre": _cut(rows, "debtor_state_at_close", DISTRESS, states),
        "reconoce_y_ofrece": _cut(rows, "difficulty_response", {"reconoce_y_ofrece"}, difficulty),
    }


def distribution(rows: list[dict], name: str) -> dict:
    return {
        arm: dict(Counter(str(value(r, name)) for r in rows if r["arm"] == arm)) for arm in ARMS
    }


def coherence(rows: list[dict]) -> dict:
    """Positivo del desenlace frente a compromiso calificado de la familia, por brazo."""
    table = {arm: Counter() for arm in ARMS}
    for row in rows:
        positive = value(row, "final_disposition") in POSITIVE
        table[row["arm"]][
            f"desenlace_{int(positive)}_compromiso_{row['_qualified_commitment']}"
        ] += 1
    return {arm: dict(counts) for arm, counts in table.items()}


def export(rows: list[dict], agreement: dict) -> dict:
    new_cases = [r for r in rows if r["_new_case"]]
    payload = {
        "preregistro": "docs/hipotesis.md §7",
        "llamadas": {arm: sum(r["arm"] == arm for r in rows) for arm in ARMS},
        "acuerdo_panel": agreement,
        "anclaje": anchoring(rows),
        "cortes": {"total": cuts(rows), "gestiones_nuevas": cuts(new_cases)},
        "distribucion": {
            name: distribution(rows, name)
            for name in ("final_disposition", "debtor_state_at_close", "difficulty_response")
        },
        "declara_haber_pagado": {
            arm: sum(value(r, "claims_already_paid") is True for r in rows if r["arm"] == arm)
            for arm in ARMS
        },
        "coherencia_con_compromiso": coherence(rows),
    }
    PUBLIC.mkdir(parents=True, exist_ok=True)
    (PUBLIC / "desenlace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # Whitelist: identificador desidentificado, brazo y categorías cerradas. Ninguna cita.
    allowed = json.loads(SCHEMA.read_text(encoding="utf-8"))["properties"]
    columns = [
        "final_disposition",
        "claims_already_paid",
        "debtor_state_at_close",
        "difficulty_response",
    ]
    with (PUBLIC / "desenlace.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["call_id", "arm", *columns])
        for row in rows:
            values = []
            for name in columns:
                v = value(row, name)
                if v not in allowed[name]["properties"]["value"]["enum"]:
                    raise ValueError(f"Valor fuera del conjunto cerrado en {name}: {v!r}")
                values.append("" if v is None else int(v) if isinstance(v, bool) else v)
            writer.writerow([row["call_id"], row["arm"], *values])
    return payload


def listening_sheet(rows: list[dict]) -> Path:
    """20 llamadas, 10 por brazo, estratificadas por desenlace y con prioridad a discrepancias.

    La hoja no muestra el voto del panel ni el brazo; la clave va en un archivo aparte.
    """
    durations = {}
    with INVENTORY.open(encoding="utf-8") as fh:
        for item in csv.DictReader(fh):
            durations[Path(item["filename"]).stem] = float(item["duration_s"])
    rng = random.Random(SEED)
    chosen = []
    for arm in ARMS:
        members = [r for r in rows if r["arm"] == arm]
        discrepant = [
            r
            for r in members
            if (value(r, "final_disposition") in POSITIVE) != (r["_qualified_commitment"] == 1)
        ]
        rng.shuffle(discrepant)
        picked = discrepant[: LISTEN_PER_ARM // 2]
        strata: dict[str, list[dict]] = {}
        for r in members:
            if r not in picked:
                strata.setdefault(str(value(r, "final_disposition")), []).append(r)
        for group in strata.values():
            rng.shuffle(group)
        while len(picked) < LISTEN_PER_ARM and any(strata.values()):
            for key in sorted(strata):
                if strata[key] and len(picked) < LISTEN_PER_ARM:
                    picked.append(strata[key].pop())
        chosen += picked
    rng.shuffle(chosen)
    with (
        SHEET.open("w", newline="", encoding="utf-8") as fh,
        SHEET_KEY.open("w", newline="", encoding="utf-8") as key,
    ):
        sheet, answer = csv.writer(fh), csv.writer(key)
        sheet.writerow(
            [
                "orden",
                "audio",
                "escuchar_desde",
                "desenlace (rechazo / sin_cierre / vago / parcial / total / no_aplica)",
                "estado_al_cierre (cooperativo / angustiado / molesto / evasivo / no_se)",
                "nota",
            ]
        )
        answer.writerow(["orden", "brazo", "stem", "panel_desenlace", "panel_estado"])
        for i, r in enumerate(chosen, 1):
            start = max(0.0, durations.get(r["_stem"], 0.0) - LISTEN_SECONDS)
            audio = f"data/raw/{r['arm']}/{r['_stem']}.wav"
            sheet.writerow([i, audio, f"{int(start // 60):02d}:{int(start % 60):02d}", "", "", ""])
            answer.writerow(
                [
                    i,
                    r["arm"],
                    r["_stem"],
                    value(r, "final_disposition"),
                    value(r, "debtor_state_at_close"),
                ]
            )
    return SHEET


def gwet_ac1(a: list[bool], b: list[bool]) -> float:
    """AC1 de Gwet para dos evaluadores y una categoría binaria."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    observed = np.mean(a == b)
    prevalence = (a.mean() + b.mean()) / 2
    chance = 2 * prevalence * (1 - prevalence)
    return float((observed - chance) / (1 - chance)) if chance < 1 else 1.0


def agreement_with_listening(sheet: Path) -> dict:
    """Acuerdo del oído con el panel, por brazo, para los dos cortes que se validan a oído.

    Acuerdo exacto y AC1 de Gwet con IC bootstrap por llamada (2.000 réplicas, semilla fija).
    Las filas sin respuesta o con «no_se» quedan fuera del corte correspondiente.
    """
    key = {}
    with SHEET_KEY.open(encoding="utf-8") as fh:
        for item in csv.DictReader(fh):
            key[item["orden"]] = item
    pairs: dict[str, dict[str, list[tuple[bool, bool]]]] = {
        cut: {arm: [] for arm in ARMS} for cut in ("positivo", "malestar_al_cierre")
    }
    with sheet.open(encoding="utf-8") as fh:
        reader = csv.reader(fh)
        next(reader)
        for row in reader:
            if not row or not row[0].strip():
                continue
            truth = key[row[0].strip()]
            heard_disposition = row[3].strip().lower()
            heard_state = row[4].strip().lower()
            if heard_disposition and heard_disposition != "no_aplica":
                panel = truth["panel_desenlace"] in POSITIVE
                pairs["positivo"][truth["brazo"]].append(
                    (heard_disposition in {"parcial", "total"}, panel)
                )
            if heard_state and heard_state != "no_se":
                panel = truth["panel_estado"] in DISTRESS
                pairs["malestar_al_cierre"][truth["brazo"]].append(
                    (heard_state in {"angustiado", "molesto"}, panel)
                )
    rng = np.random.default_rng(SEED)
    out = {}
    for cut, by_arm in pairs.items():
        out[cut] = {}
        for arm, items in by_arm.items():
            if not items:
                out[cut][arm] = {"n": 0}
                continue
            heard, panel = zip(*items, strict=True)
            boot = []
            for _ in range(2000):
                idx = rng.integers(0, len(items), len(items))
                boot.append(gwet_ac1([heard[i] for i in idx], [panel[i] for i in idx]))
            out[cut][arm] = {
                "n": len(items),
                "acuerdo_exacto": float(np.mean(np.asarray(heard) == np.asarray(panel))),
                "ac1": gwet_ac1(list(heard), list(panel)),
                "ac1_ic95": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
            }
    (PUBLIC / "desenlace_validacion.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Desenlace y reacción del interlocutor.")
    parser.add_argument("--from-workflow", type=Path, help="salida JSON del panel de desenlace")
    parser.add_argument("--listening-sheet", action="store_true", help="genera la hoja de escucha")
    parser.add_argument("--agreement", type=Path, help="hoja de escucha llena por el usuario")
    args = parser.parse_args()

    if args.agreement:
        print(json.dumps(agreement_with_listening(args.agreement), ensure_ascii=False, indent=2))
        return

    if args.from_workflow:
        if not args.from_workflow.exists():
            raise SystemExit(f"No existe la salida del workflow: {args.from_workflow}")
        payload = json.loads(args.from_workflow.read_text(encoding="utf-8"))
        result = payload.get("result", payload)
        print(f"Guardadas {persist(result['anotaciones'], ANNOTATIONS)} anotaciones")

    agreement = consolidate()
    rows = load()
    if args.listening_sheet:
        print(f"Hoja: {listening_sheet(rows).relative_to(ROOT)}")
        return
    payload = export(rows, agreement)
    for name, cut in payload["cortes"]["total"].items():
        ci = (
            f"{cut['diff_pp']:+.0f} pp [{cut['ci_low_pp']:+.0f}, {cut['ci_high_pp']:+.0f}]"
            if "diff_pp" in cut
            else "solo conteos"
        )
        print(
            f"  {name:<22} IA {cut['k_ia']}/{cut['n_ia']} · humanos "
            f"{cut['k_humano']}/{cut['n_humano']} · {ci}"
        )


if __name__ == "__main__":
    main()
