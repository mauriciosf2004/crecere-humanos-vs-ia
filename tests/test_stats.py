"""Verifica los helpers estadísticos contra valores publicados.

Cada test fija un número de la literatura o una propiedad exacta: un error silencioso
aquí cambiaría una conclusión del reporte sin que nadie lo note.
"""

import numpy as np
import pytest

from src.stats import (
    audit_sample_size,
    cliffs_delta,
    compare_proportions,
    fisher_power,
    hodges_lehmann,
    sample_size_per_arm,
)


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


def test_newcombe_interval_matches_published_example():
    """Newcombe (1998), método 10: 56/70 frente a 48/80 da [0,0524; 0,3339]."""
    result = compare_proportions(56, 70, 48, 80)
    assert abs(result.ci_low_pp - 5.24) < 0.01
    assert abs(result.ci_high_pp - 33.39) < 0.01


def test_sample_size_matches_cohen_table():
    """Cohen (1988), tabla 6.4.1: h = 0,20, alfa 0,05 bilateral y potencia 0,80 dan 392."""
    base = 0.5
    target = np.sin(np.pi / 4 + 0.1) ** 2  # desde 0,5, esta tasa da h = 0,20 exacto
    assert 390 <= sample_size_per_arm(base, target - base) <= 394


def test_planning_is_less_conservative_than_exact_fisher():
    """Para el umbral que Fisher exacto sitúa en 50 por brazo, la aproximación pide menos."""
    assert sample_size_per_arm(0.30, 0.29) <= 50


def test_audit_sample_size_barely_grows_with_the_corpus():
    """La afirmación que sostiene el argumento de escala del informe.

    Si esto dejara de ser cierto, la sección de control de calidad estaría mintiendo: el
    costo humano de auditar dejaría de ser plano y el método no serviría en producción.
    """
    cien = audit_sample_size(0.85, 0.10, population=100)
    cien_mil = audit_sample_size(0.85, 0.10, population=100_000)
    diez_millones = audit_sample_size(0.85, 0.10, population=10_000_000)
    # Multiplicar el corpus por cien mil no cambia la muestra ni en una llamada.
    assert cien_mil == diez_millones
    # Y frente a un corpus de cien, la muestra crece menos de un 50 %.
    assert cien < cien_mil < 1.5 * cien
    # Como fracción, el trabajo se desploma: del 34 % al 0,05 %.
    assert cien / 100 > 0.3
    assert cien_mil / 100_000 < 0.001


def test_audit_sample_size_needs_four_times_the_calls_for_half_the_error():
    """La precisión va con la raíz de la muestra: exigir el doble cuesta el cuádruple."""
    assert audit_sample_size(0.85, 0.05) == pytest.approx(
        4 * audit_sample_size(0.85, 0.10), rel=0.02
    )
