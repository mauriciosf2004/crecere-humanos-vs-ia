"""Verifica los helpers estadísticos contra valores conocidos.

Se testea esto y no el pipeline porque es el único código donde un error
silencioso cambiaría una conclusión del reporte sin que nadie lo note.
"""

import numpy as np

from src.stats import cliffs_delta, compare_proportions, fisher_power, hodges_lehmann


def test_fisher_matches_known_value():
    """Tabla clásica de la dama del té (Fisher): p bilateral = 0.4857."""
    result = compare_proportions(3, 4, 1, 4)
    assert abs(result.p_value - 0.4857) < 1e-3


def test_cliffs_delta_bounds():
    """Separación total da +1; distribuciones idénticas dan 0."""
    assert cliffs_delta(np.array([10, 11, 12]), np.array([1, 2, 3])) == 1.0
    assert cliffs_delta(np.array([1, 2, 3]), np.array([1, 2, 3])) == 0.0


def test_hodges_lehmann_recovers_shift():
    """Un desplazamiento constante se recupera exactamente."""
    base = np.array([1.0, 5.0, 9.0, 14.0])
    assert hodges_lehmann(base + 7.0, base) == 7.0


def test_power_is_low_for_small_differences():
    """El hecho que gobierna el reporte: 30% vs 40% con n=50/50 es indetectable."""
    assert fisher_power(0.30, 0.40, 50, 50) < 0.20


def test_confidence_interval_contains_difference():
    result = compare_proportions(20, 50, 10, 50)
    assert result.ci_low_pp < result.diff_pp < result.ci_high_pp
