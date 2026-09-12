"""Invariantes del procedimiento de contraste.

No se simula el FWER aquí —eso se hizo aparte y tarda minutos—, sino las
propiedades que deben cumplirse en cada corrida y cuya violación cambiaría una
conclusión sin avisar.
"""

import numpy as np

from src.analyze import global_test, westfall_young


def _rng():
    return np.random.default_rng(0)


def test_global_test_returns_valid_pvalue():
    matrix = _rng().integers(0, 2, size=(40, 6)).astype(float)
    is_ai = np.array([True] * 20 + [False] * 20)
    p = global_test(matrix, is_ai, _rng(), permutations=400)
    assert 0 < p <= 1


def test_global_test_detects_a_blatant_difference():
    """Un brazo todo a uno y el otro todo a cero no puede salir no significativo."""
    matrix = np.vstack([np.ones((20, 5)), np.zeros((20, 5))])
    is_ai = np.array([True] * 20 + [False] * 20)
    assert global_test(matrix, is_ai, _rng(), permutations=400) < 0.01


def test_adjustment_never_lowers_significance():
    """El p ajustado no puede ser menor que la proporción de permutaciones extremas."""
    matrix = _rng().integers(0, 2, size=(60, 8)).astype(float)
    is_ai = np.array([True] * 30 + [False] * 30)
    adjusted = westfall_young(matrix, is_ai, _rng(), permutations=400)
    assert np.all((adjusted >= 0) & (adjusted <= 1))


def test_step_down_is_monotone_in_effect_order():
    """Mayor efecto observado no puede recibir un p ajustado mayor: rompería el step-down."""
    matrix = _rng().integers(0, 2, size=(60, 6)).astype(float)
    matrix[:30, 0] = 1.0  # efecto grande en la primera
    matrix[30:, 0] = 0.0
    is_ai = np.array([True] * 30 + [False] * 30)
    adjusted = westfall_young(matrix, is_ai, _rng(), permutations=400)
    effects = np.abs(matrix[is_ai].mean(axis=0) - matrix[~is_ai].mean(axis=0))
    order = np.argsort(-effects)
    assert np.all(np.diff(adjusted[order]) >= -1e-12)
