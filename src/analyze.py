"""Contrasta la familia de ocho variables entre brazos.

El procedimiento tiene dos niveles, en el orden de la pregunta del encargo: primero
"¿existen diferencias?", después "¿cuáles?".

  Nivel 1  Test global por permutación sobre el perfil completo de las ocho
           variables. Una sola pregunta, un solo p-valor, sin multiplicidad.
  Nivel 2  Westfall-Young step-down sobre la familia, si el nivel 1 rechaza.

El control del error por familia lo pone Westfall-Young por sí solo, no la compuerta.
Se eligió frente a Bonferroni o Holm porque aprovecha la correlación entre variables,
que aquí es alta —varias miden partes del mismo guion—, y lo discreto de los datos
binarios. La compuerta no añade garantías; ordena la respuesta, y si el perfil conjunto
no difiriera evitaría interpretar variables sueltas.

El test global y Westfall-Young son por permutación Monte Carlo (10.000 reordenamientos,
semilla fija), sin supuestos distribucionales. Cada contraste lleva además su diferencia
en puntos porcentuales con el IC de Newcombe y el p de Fisher exacto, porque con esta
potencia el p-valor solo no dice si la diferencia importa.

Además del contraste, el módulo mide la composición de las carteras. Los brazos no
atacaron las mismas cuentas —los humanos retoman acuerdos previos y la IA no—, así que
Westfall-Young se repite dentro de las gestiones nuevas, el único tipo de gestión con
llamadas de los dos brazos.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy import stats
from scipy.spatial.distance import cdist

from src.stats import (
    cliffs_delta,
    compare_proportions,
    hodges_lehmann,
    minimum_detectable_effect,
    sample_size_per_arm,
)

ROOT = Path(__file__).resolve().parent.parent
EXTRACTIONS = ROOT / "data" / "interim" / "extractions"
CONSENSUS = ROOT / "data" / "interim" / "consensus"
PUBLIC = ROOT / "data" / "public"

PERMUTATIONS = 10_000
SEED = 20260915
PLANNING_BASE = 0.30  # tasa de referencia para el umbral detectable y el piloto
PLANNING_POWER = 0.80

# La familia, en el orden en que se declaró antes de medir. El texto es la etiqueta
# que ve el lector del informe; la hipótesis es la que se registró de antemano.
FAMILY = [
    ("legal_department_framing", "Se presenta desde un área jurídica o de embargos", "IA ≫ humano"),
    ("offer_expiry_claim", "Afirma que la oferta caduca hoy", "IA ≫ humano"),
    (
        "situational_legal_pressure",
        "Plantea un proceso legal como consecuencia de no pagar",
        "IA ≫ humano",
    ),
    ("credit_benefit_promised", "Promete beneficio en el historial crediticio", "humano ≫ IA"),
    ("confidentiality_gate", "Invoca confidencialidad o verifica identidad", "IA > humano"),
    ("qualified_payment_commitment", "Obtiene compromiso de pago calificado", "humano > IA"),
    ("quantified_proposal_stated", "Enuncia una propuesta con cifras", "sin diferencia"),
    ("installment_or_partial_offer", "Ofrece cuotas o abono parcial", "sin diferencia"),
]

# El compromiso de pago es ordinal (0 sin compromiso, 1 vago, 2 calificado) y la
# celda de la familia es solo el nivel 2. Colapsarlo con bool() contaría los
# compromisos vagos como calificados, que es justo la distinción que importa.
ORDINAL = {"qualified_payment_commitment": 2}

# Variables de contexto: no son desenlaces, describen a quién se llamó. Salen al CSV
# público porque son categóricas cerradas; el conjunto de valores se valida para que
# ningún texto libre del modelo pueda colarse en un archivo versionado.
CONTEXT = {
    "prior_agreement_followup": {True, False},
    "effective_contact": {"titular", "tercero", "no_determinable"},
}


@dataclass(frozen=True)
class Contrast:
    """El contraste de una variable, con todo lo que hace falta para reportarlo."""

    name: str
    label: str
    hypothesis: str
    k_ai: int
    k_human: int
    n_ai: int
    n_human: int
    diff_pp: float
    ci_low_pp: float
    ci_high_pp: float
    p_raw: float
    p_adjusted: float | None = None


def _raw(row: dict, key: str):
    cell_value = row.get(key)
    return cell_value.get("value") if isinstance(cell_value, dict) else cell_value


def cell(row: dict, key: str) -> int:
    """Valor 0/1 de una variable de la familia en una fila anotada.

    Una celda vacía —sin mayoría en el panel— cuenta como 0: no se afirma una conducta
    que no quedó respaldada.
    """
    raw = _raw(row, key)
    if key in ORDINAL:
        return int(raw == ORDINAL[key])
    return int(bool(raw))


def load_rows(source: Path = CONSENSUS) -> list[dict]:
    """Las anotaciones de una fuente, humano primero y luego IA, en orden estable.

    La fuente es la extracción original de un solo modelo o el consenso del panel de tres.
    """
    rows = [
        json.loads(path.read_text(encoding="utf-8"))
        for arm in ("humano", "ia")
        for path in sorted((source / arm).glob("*.json"))
    ]
    if not rows:
        step = "make annotate" if source == CONSENSUS else "make extract"
        raise SystemExit(
            f"No hay anotaciones en {source.relative_to(ROOT)}. Corre `{step}`, "
            "que necesita las transcripciones de `make transcribe`."
        )
    arms = {row["arm"] for row in rows}
    if arms != {"humano", "ia"}:
        raise ValueError(f"Faltan anotaciones de un brazo: solo hay {sorted(arms)}.")
    return rows


def load_table(source: Path = CONSENSUS) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Matriz (llamadas x variables) de 0/1, el vector de brazo y los identificadores."""
    rows = load_rows(source)
    names = [name for name, _, _ in FAMILY]
    matrix = np.array([[cell(row, name) for name in names] for row in rows], dtype=float)
    is_ai = np.array([row["arm"] == "ia" for row in rows], dtype=bool)
    return matrix, is_ai, [row["call_id"] for row in rows]


def global_test(
    matrix: np.ndarray,
    is_ai: np.ndarray,
    rng: np.random.Generator,
    permutations: int = PERMUTATIONS,
) -> float:
    """Distancia de energía entre los perfiles de los dos brazos, por permutación.

    Responde la pregunta del encargo tal cual está formulada: ¿los dos brazos se
    comportan distinto? Gana potencia cuando la diferencia está repartida entre
    varias variables, que es el escenario esperado con un agente guionizado.
    """

    def energy(group: np.ndarray) -> float:
        a, b = matrix[group], matrix[~group]
        return 2 * cdist(a, b).mean() - cdist(a, a).mean() - cdist(b, b).mean()

    observed = energy(is_ai)
    null = np.array([energy(rng.permutation(is_ai)) for _ in range(permutations)])
    return float((np.sum(null >= observed) + 1) / (permutations + 1))


def westfall_young(
    matrix: np.ndarray,
    is_ai: np.ndarray,
    rng: np.random.Generator,
    permutations: int = PERMUTATIONS,
) -> np.ndarray:
    """p-valores ajustados por step-down max-T, con la diferencia de tasas como estadístico.

    El máximo se toma sobre las variables aún vivas en cada paso, así que la
    distribución nula incorpora la correlación real entre ellas en vez de suponerlas
    independientes.
    """

    def statistic(group: np.ndarray) -> np.ndarray:
        return np.abs(matrix[group].mean(axis=0) - matrix[~group].mean(axis=0))

    observed = statistic(is_ai)
    order = np.argsort(-observed)
    null = np.array([statistic(rng.permutation(is_ai))[order] for _ in range(permutations)])

    # máximo sucesivo de derecha a izquierda: en el paso j solo compiten las que
    # quedan por debajo en el orden observado
    successive = np.maximum.accumulate(null[:, ::-1], axis=1)[:, ::-1]
    # (r+1)/(B+1): un p-valor por permutación no puede ser cero exacto
    adjusted = ((successive >= observed[order]).sum(axis=0) + 1) / (permutations + 1)
    adjusted = np.maximum.accumulate(adjusted)  # monotonía que exige el step-down

    out = np.empty(len(observed))
    out[order] = adjusted
    return out


def analyse(source: Path = CONSENSUS) -> tuple[float, list[Contrast]]:
    matrix, is_ai, _ = load_table(source)
    rng = np.random.default_rng(SEED)

    p_global = global_test(matrix, is_ai, rng)
    adjusted = westfall_young(matrix, is_ai, rng) if p_global < 0.05 else None

    contrasts: list[Contrast] = []
    for index, (name, label, hypothesis) in enumerate(FAMILY):
        column = matrix[:, index]
        k_ai, k_human = int(column[is_ai].sum()), int(column[~is_ai].sum())
        n_ai, n_human = int(is_ai.sum()), int((~is_ai).sum())
        test = compare_proportions(k_ai, n_ai, k_human, n_human)
        contrasts.append(
            Contrast(
                name=name,
                label=label,
                hypothesis=hypothesis,
                k_ai=k_ai,
                k_human=k_human,
                n_ai=n_ai,
                n_human=n_human,
                diff_pp=test.diff_pp,
                ci_low_pp=test.ci_low_pp,
                ci_high_pp=test.ci_high_pp,
                p_raw=test.p_value,
                p_adjusted=None if adjusted is None else float(adjusted[index]),
            )
        )
    return p_global, contrasts


def stratified(rows: list[dict], name: str) -> dict:
    """Recuentos de una variable dentro de cada estrato de acuerdo previo.

    Un valor ausente cuenta como "no" (hay uno en cien). Con el consenso, la IA no tiene
    ninguna llamada que retome un acuerdo previo, así que en ese estrato no hay contraste
    posible: la comparación ajustada es Westfall-Young dentro de las gestiones nuevas
    (p_ajustado_nuevas en export). Aquí se publican las celdas, para que eso se vea.
    """
    strata = []
    for label, flag in (("nuevo", False), ("previo", True)):
        members = [r for r in rows if bool(_raw(r, "prior_agreement_followup")) is flag]
        ai = [r for r in members if r["arm"] == "ia"]
        human = [r for r in members if r["arm"] == "humano"]
        strata.append(
            {
                "estrato": label,
                "k_ia": sum(cell(r, name) for r in ai),
                "n_ia": len(ai),
                "k_humano": sum(cell(r, name) for r in human),
                "n_humano": len(human),
            }
        )
    return {"estratos": strata}


def composition(rows: list[dict]) -> list[dict]:
    """Quién estaba al otro lado de la línea, en las dos señales medibles desde el audio.

    Sin metadatos es la única forma de ver si los brazos atacaron carteras
    comparables. No lo hicieron, y eso condiciona cómo se lee el compromiso de pago.
    """
    ai = [r for r in rows if r["arm"] == "ia"]
    human = [r for r in rows if r["arm"] == "humano"]
    undetermined = (None, "no_determinable")
    out = []
    for key, positive, label in (
        ("prior_agreement_followup", True, "Retoma un acuerdo de pago previo"),
        ("effective_contact", "titular", "Habla con el titular de la deuda"),
    ):
        k_ai = sum(_raw(r, key) == positive for r in ai)
        k_human = sum(_raw(r, key) == positive for r in human)
        test = compare_proportions(k_ai, len(ai), k_human, len(human))
        out.append(
            {
                "variable": key,
                "etiqueta": label,
                "k_ia": k_ai,
                "n_ia": len(ai),
                "k_humano": k_human,
                "n_humano": len(human),
                "diff_pp": test.diff_pp,
                "ci_low_pp": test.ci_low_pp,
                "ci_high_pp": test.ci_high_pp,
                "p": test.p_value,
                "indeterminado_ia": sum(_raw(r, key) in undetermined for r in ai),
                "indeterminado_humano": sum(_raw(r, key) in undetermined for r in human),
            }
        )
    return out


def duration_contrast() -> dict:
    """El nulo de duración, con el signo en la convención IA − humano.

    Mann-Whitney bilateral; con empates, scipy usa la aproximación normal.
    """
    path = PUBLIC / "durations.csv"
    if not path.exists():
        raise FileNotFoundError(f"Falta {path.relative_to(ROOT)}. Corre `make inventory`.")
    with path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    ai = np.array([float(r["duration_s"]) for r in rows if r["arm"] == "ia"])
    human = np.array([float(r["duration_s"]) for r in rows if r["arm"] == "humano"])
    return {
        "mediana_ia_s": float(np.median(ai)),
        "mediana_humano_s": float(np.median(human)),
        "hodges_lehmann_s": round(hodges_lehmann(ai, human), 1),
        "cliffs_delta": round(cliffs_delta(ai, human), 3),
        "p_mann_whitney": float(stats.mannwhitneyu(ai, human, alternative="two-sided").pvalue),
    }


def panel_agreement(rows: list[dict]) -> dict:
    """Con cuántos votos se decidió cada celda, cuando los datos vienen del panel.

    Con la extracción original no hay votos y devuelve un diccionario vacío.
    """
    counts: dict[str, Counter] = {}
    for row in rows:
        for field, agreement in row.get("_acuerdo", {}).items():
            counts.setdefault(field, Counter())[agreement] += 1
    return {field: dict(counter) for field, counter in counts.items()}


def _context_value(row: dict, key: str):
    raw = _raw(row, key)
    if raw is None:
        return ""
    if raw not in CONTEXT[key]:
        raise ValueError(f"Valor fuera del conjunto cerrado en {key}: {raw!r}")
    return int(raw) if isinstance(raw, bool) else raw


def export(p_global: float, contrasts: list[Contrast], source: Path = CONSENSUS) -> None:
    """Escribe la tabla desidentificada y los efectos que consume el informe.

    Solo salen variables derivadas y categorías cerradas: ni una palabra del texto
    de la llamada. Es lo que permite versionar el resultado sin publicar datos de
    deudores reales.
    """
    PUBLIC.mkdir(parents=True, exist_ok=True)
    rows = load_rows(source)
    names = [name for name, _, _ in FAMILY]

    with (PUBLIC / "features.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["call_id", "arm", *names, *CONTEXT])
        for row in rows:
            writer.writerow(
                [
                    row["call_id"],
                    row["arm"],
                    *(cell(row, name) for name in names),
                    *(_context_value(row, key) for key in CONTEXT),
                ]
            )

    # La comparación "dentro del mismo tipo de gestión" también se corrige por las ocho
    # variables: Westfall-Young sobre las gestiones nuevas, que es el único estrato con los
    # dos brazos. Sin compuerta: Westfall-Young controla el error por familia por sí solo.
    new = np.array([not bool(_raw(row, "prior_agreement_followup")) for row in rows])
    matrix, is_ai, _ = load_table(source)
    adjusted_new = westfall_young(matrix[new], is_ai[new], np.random.default_rng(SEED + 1))

    n_ai, n_human = contrasts[0].n_ai, contrasts[0].n_human
    # Tres suelos de sensibilidad, no uno. El del contraste suelto es el más optimista de los
    # tres y publicarlo solo exagera lo que el estudio puede ver: la inferencia que el informe
    # declara usar corrige por las ocho comparaciones, y el KPI comercial se mide sobre los
    # contactos con titular, que son menos llamadas.
    composition_rows = composition(rows)
    titular = next(i for i in composition_rows if i["variable"] == "effective_contact")
    floors = {
        "suelto": minimum_detectable_effect(PLANNING_BASE, n_ai, n_human),
        "familia": minimum_detectable_effect(
            PLANNING_BASE, n_ai, n_human, alpha=0.05 / len(contrasts)
        ),
        "titular": minimum_detectable_effect(PLANNING_BASE, titular["k_ia"], titular["k_humano"]),
    }
    payload = {
        "p_global": p_global,
        "fuente": source.name,
        "acuerdo_panel": panel_agreement(rows),
        "permutations": PERMUTATIONS,
        "seed": SEED,
        "mde_pp": round(floors["suelto"], 1),
        "mde_suelos_pp": {k: round(v, 1) for k, v in floors.items()},
        "mde_tasa_base": PLANNING_BASE,
        "potencia_plan": PLANNING_POWER,
        "piloto_n_por_brazo": {
            str(delta): sample_size_per_arm(PLANNING_BASE, delta / 100, power=PLANNING_POWER)
            for delta in (10, 15)
        },
        "contrastes": [
            {
                "variable": c.name,
                "etiqueta": c.label,
                "hipotesis": c.hypothesis,
                "k_ia": c.k_ai,
                "n_ia": c.n_ai,
                "k_humano": c.k_human,
                "n_humano": c.n_human,
                "diff_pp": c.diff_pp,
                "ci_low_pp": c.ci_low_pp,
                "ci_high_pp": c.ci_high_pp,
                "p_raw": c.p_raw,
                "p_ajustado": c.p_adjusted,
                "p_ajustado_nuevas": float(adjusted_new[i]),
                "estratificado": stratified(rows, c.name),
            }
            for i, c in enumerate(contrasts)
        ],
        "composicion": composition_rows,
        "duracion": duration_contrast(),
    }
    (PUBLIC / "effects.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Contrasta la familia de ocho variables.")
    parser.add_argument(
        "--source",
        choices=("extraccion", "consenso"),
        default="consenso",
        help="extracción original de un modelo, o consenso del panel de tres",
    )
    source = CONSENSUS if parser.parse_args().source == "consenso" else EXTRACTIONS
    p_global, contrasts = analyse(source)
    export(p_global, contrasts, source)
    effects = json.loads((PUBLIC / "effects.json").read_text(encoding="utf-8"))

    print(f"Nivel 1 · test global por permutación: p = {p_global:.5f}")
    print("  la compuerta abre\n" if p_global < 0.05 else "  la compuerta NO abre\n")
    print(
        f"{'variable':<32}{'IA':>8}{'humano':>9}{'dif':>6}{'IC 95%':>12}{'p aj.':>8}{'p nuevas':>9}"
    )
    for item in sorted(effects["contrastes"], key=lambda x: -abs(x["diff_pp"])):
        ci = f"[{item['ci_low_pp']:+.0f},{item['ci_high_pp']:+.0f}]"
        p_adj = "—" if item["p_ajustado"] is None else f"{item['p_ajustado']:.4f}"
        p_new = f"{item['p_ajustado_nuevas']:.4f}"
        print(
            f"{item['etiqueta'][:31]:<32}{item['k_ia']:>4}/{item['n_ia']:<3}"
            f"{item['k_humano']:>5}/{item['n_humano']:<3}{item['diff_pp']:>+6.0f}"
            f"{ci:>12}{p_adj:>8}{p_new:>9}"
        )

    print("\nComposición de las carteras")
    for item in effects["composicion"]:
        print(
            f"  {item['etiqueta']:<34} IA {item['k_ia']}/{item['n_ia']}  "
            f"humano {item['k_humano']}/{item['n_humano']}  {item['diff_pp']:+.0f} pp  "
            f"(indeterminadas: IA {item['indeterminado_ia']}, "
            f"humano {item['indeterminado_humano']})"
        )

    d = effects["duracion"]
    print(
        f"\nDuración: mediana IA {d['mediana_ia_s']:.0f} s vs humano "
        f"{d['mediana_humano_s']:.0f} s · "
        f"HL {d['hodges_lehmann_s']:+.1f} s · "
        f"δ {d['cliffs_delta']:+.3f} · p {d['p_mann_whitney']:.3f}"
    )
    print(f"MDE con tasa base 30 %: {effects['mde_pp']} pp")


if __name__ == "__main__":
    main()
