"""Contrasta la familia de ocho variables entre brazos.

El procedimiento tiene dos niveles y ese orden replica la pregunta del encargo:
primero "¿existen diferencias?", después "¿cuáles las explican?".

  Nivel 1  Test global por permutación sobre el perfil completo de las ocho
           variables. Una sola pregunta, un solo p-valor, sin multiplicidad.
  Nivel 2  Solo si el nivel 1 rechaza: Westfall-Young step-down sobre la familia.
           Controla el error por familia al 5% de forma exacta y, a diferencia de
           Bonferroni o Holm, aprovecha la correlación entre variables, que aquí
           es alta porque varias miden partes del mismo guion.

Como el nivel 1 actúa de compuerta, el error por familia del procedimiento completo
queda en 5% sin necesidad de corregir nada más (closed testing).

Toda la inferencia es por permutación: es exacta con n=50 por brazo y no asume
ninguna distribución. Y toda comparación se reporta con su tamaño de efecto en
puntos porcentuales y su intervalo, porque con esta muestra el p-valor solo no
dice si la diferencia importa.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.spatial.distance import cdist

from src.stats import compare_proportions

ROOT = Path(__file__).resolve().parent.parent
EXTRACTIONS = ROOT / "data" / "interim" / "extractions"
PUBLIC = ROOT / "data" / "public"

PERMUTATIONS = 10_000  # se reduce en los tests vía monkeypatch si hiciera falta
SEED = 20260915

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
    ("quantified_proposal_stated", "Enuncia una propuesta con cifras", "nulo declarado"),
    ("installment_or_partial_offer", "Ofrece cuotas o abono parcial", "nulo declarado"),
]


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


def load_table() -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Matriz (n_llamadas x n_variables) de 0/1, y el vector de brazo."""
    rows = [
        json.loads(path.read_text(encoding="utf-8"))
        for arm in ("humano", "ia")
        for path in sorted((EXTRACTIONS / arm).glob("*.json"))
    ]
    names = [name for name, _, _ in FAMILY]

    def value(row: dict, key: str) -> int:
        cell = row.get(key)
        raw = cell.get("value") if isinstance(cell, dict) else cell
        return int(bool(raw))

    matrix = np.array([[value(row, name) for name in names] for row in rows], dtype=float)
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
    adjusted = (successive >= observed[order]).mean(axis=0)
    adjusted = np.maximum.accumulate(adjusted)  # monotonía que exige el step-down

    out = np.empty(len(observed))
    out[order] = adjusted
    return out


def analyse() -> tuple[float, list[Contrast]]:
    matrix, is_ai, _ = load_table()
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


def main() -> None:
    p_global, contrasts = analyse()
    print(f"Nivel 1 · test global por permutación: p = {p_global:.5f}")
    print("  la compuerta abre\n" if p_global < 0.05 else "  la compuerta NO abre\n")
    print(f"{'variable':<32}{'IA':>8}{'humano':>9}{'dif pp':>9}{'IC 95%':>17}{'p aj.':>9}")
    for c in sorted(contrasts, key=lambda x: -abs(x.diff_pp)):
        ci = f"[{c.ci_low_pp:+.0f}, {c.ci_high_pp:+.0f}]"
        padj = "—" if c.p_adjusted is None else f"{c.p_adjusted:.4f}"
        print(
            f"{c.label[:31]:<32}{c.k_ai:>4}/{c.n_ai:<3}{c.k_human:>5}/{c.n_human:<3}"
            f"{c.diff_pp:>+9.0f}{ci:>17}{padj:>9}"
        )


if __name__ == "__main__":
    main()
