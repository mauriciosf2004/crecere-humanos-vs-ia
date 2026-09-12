"""Comparaciones humano vs IA con n=50 por brazo.

La muestra es pequeña y eso condiciona qué se puede afirmar. Con Fisher exacto
bilateral, alfa=0.05 y 80% de potencia, la diferencia mínima detectable en una
tasa es de ~29 puntos porcentuales. Por eso aquí no hay una función que devuelva
un p-valor suelto: toda comparación devuelve también el tamaño del efecto y su
intervalo de confianza, que es lo que se reporta.

Todo lo necesario está en scipy; no hace falta statsmodels.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats


@dataclass(frozen=True)
class ProportionTest:
    """Comparación de dos proporciones."""

    n1: int
    k1: int
    n2: int
    k2: int
    p_value: float
    diff_pp: float
    ci_low_pp: float
    ci_high_pp: float

    def __str__(self) -> str:
        return (
            f"{self.k1}/{self.n1} ({100 * self.k1 / self.n1:.0f}%) vs "
            f"{self.k2}/{self.n2} ({100 * self.k2 / self.n2:.0f}%) · "
            f"dif {self.diff_pp:+.0f} pp "
            f"[IC95 {self.ci_low_pp:+.0f}, {self.ci_high_pp:+.0f}] · p={self.p_value:.3f}"
        )


def _wilson(k: int, n: int, z: float = 1.959963985) -> tuple[float, float]:
    """Intervalo de Wilson para una proporción. Base del IC de Newcombe."""
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


def compare_proportions(k1: int, n1: int, k2: int, n2: int) -> ProportionTest:
    """Fisher exacto + IC de Newcombe para la diferencia.

    Fisher en vez de chi-cuadrado porque con estos n las celdas esperadas quedan
    pequeñas. Newcombe en vez de bootstrap porque es cerrado y se comporta mejor
    con proporciones extremas.
    """
    p_value = stats.fisher_exact([[k1, n1 - k1], [k2, n2 - k2]], alternative="two-sided")[1]
    low1, high1 = _wilson(k1, n1)
    low2, high2 = _wilson(k2, n2)
    diff = k1 / n1 - k2 / n2
    ci_low = diff - np.hypot(k1 / n1 - low1, high2 - k2 / n2)
    ci_high = diff + np.hypot(high1 - k1 / n1, k2 / n2 - low2)
    return ProportionTest(
        n1=n1,
        k1=k1,
        n2=n2,
        k2=k2,
        p_value=float(p_value),
        diff_pp=100 * diff,
        ci_low_pp=100 * ci_low,
        ci_high_pp=100 * ci_high,
    )


def cliffs_delta(a: np.ndarray, b: np.ndarray) -> float:
    """Tamaño de efecto no paramétrico. |d|<0.15 insignificante, 0.33 mediano, 0.47 grande."""
    diff = np.subtract.outer(np.asarray(a), np.asarray(b))
    return float((np.sum(diff > 0) - np.sum(diff < 0)) / diff.size)


def hodges_lehmann(a: np.ndarray, b: np.ndarray) -> float:
    """Diferencia típica entre los grupos: la mediana de todas las diferencias por pares.

    Es el estimador que acompaña a Mann-Whitney, igual que la media acompaña al test t.
    """
    return float(np.median(np.subtract.outer(np.asarray(a), np.asarray(b))))


def _fisher_pvalue_table(n1: int, n2: int, alpha: float) -> np.ndarray:
    """Matriz booleana (n1+1) x (n2+1): ¿rechaza Fisher esta tabla?

    El p-valor de Fisher depende sólo del total de éxitos m = k1 + k2, porque el
    test condiciona en los márgenes: bajo H0, k1 sigue una hipergeométrica. Eso
    permite calcular una pmf por cada m (101 en total) en vez de un test por cada
    tabla (2601), que es la diferencia entre milisegundos y minutos.
    """
    total = n1 + n2
    reject = np.zeros((n1 + 1, n2 + 1), dtype=bool)
    for m in range(total + 1):
        support = np.arange(max(0, m - n2), min(n1, m) + 1)
        pmf = stats.hypergeom.pmf(support, total, m, n1)
        # p-valor bilateral: masa de las tablas al menos tan improbables como la observada
        p_values = np.array([pmf[pmf <= pmf[i] * (1 + 1e-7)].sum() for i in range(len(support))])
        for k1, p_value in zip(support, p_values, strict=True):
            k2 = m - k1
            if 0 <= k2 <= n2:
                reject[k1, k2] = p_value < alpha
    return reject


def fisher_power(p1: float, p2: float, n1: int, n2: int, alpha: float = 0.05) -> float:
    """Potencia EXACTA de Fisher bilateral, por enumeración completa de las tablas.

    No es una aproximación normal: pesa cada tabla posible por su probabilidad
    binomial y suma las que rechazan. Se usa para declarar la diferencia mínima
    detectable con el denominador real de cada métrica, no con una cifra global.
    """
    reject = _fisher_pvalue_table(n1, n2, alpha)
    w1 = stats.binom.pmf(np.arange(n1 + 1), n1, p1)
    w2 = stats.binom.pmf(np.arange(n2 + 1), n2, p2)
    return float(np.outer(w1, w2)[reject].sum())


def minimum_detectable_effect(
    baseline: float, n1: int, n2: int, target_power: float = 0.80
) -> float:
    """A cuántos puntos porcentuales del baseline hay que llegar para tener target_power."""
    low, high = baseline, 0.999
    for _ in range(20):
        mid = (low + high) / 2
        if fisher_power(baseline, mid, n1, n2) < target_power:
            low = mid
        else:
            high = mid
    return 100 * (high - baseline)


def sample_size_per_arm(base: float, delta: float, alpha: float = 0.05, power: float = 0.80) -> int:
    """Llamadas por brazo para detectar un aumento de `delta` sobre una tasa `base`.

    Es para planificar el piloto, no para analizar: usa la aproximación normal sobre la
    transformación arcoseno (h de Cohen), que es el estándar de planificación. Fisher
    exacto, con el que se analizaría después, es algo más conservador, así que el número
    que devuelve es un mínimo.
    """
    h = abs(2 * np.arcsin(np.sqrt(base + delta)) - 2 * np.arcsin(np.sqrt(base)))
    z = stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(power)
    return int(np.ceil(2 * (z / h) ** 2))
