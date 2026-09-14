"""Invariantes del procedimiento de contraste.

No se simula el FWER aquí —eso se hizo aparte y tarda minutos—, sino las
propiedades que deben cumplirse en cada corrida y cuya violación cambiaría una
conclusión sin avisar.
"""

import numpy as np

from src.analyze import cell, global_test, westfall_young


def _rng():
    return np.random.default_rng(0)


def test_global_test_detects_a_blatant_difference():
    """Un brazo todo a uno y el otro todo a cero no puede salir no significativo."""
    matrix = np.vstack([np.ones((20, 5)), np.zeros((20, 5))])
    is_ai = np.array([True] * 20 + [False] * 20)
    assert global_test(matrix, is_ai, _rng(), permutations=400) < 0.01


def test_westfall_young_matches_an_independent_max_t():
    """El menor p ajustado es el max-T de un paso, y ninguno queda por debajo de su marginal.

    Se rehace la nula con las mismas permutaciones. Si el ajuste se quedara en los p
    marginales perdería el control del error por familia, y este test lo detectaría.
    """
    matrix = _rng().integers(0, 2, size=(60, 8)).astype(float)
    is_ai = np.array([True] * 30 + [False] * 30)
    permutations = 400
    adjusted = westfall_young(matrix, is_ai, np.random.default_rng(1), permutations)

    def statistic(group):
        return np.abs(matrix[group].mean(axis=0) - matrix[~group].mean(axis=0))

    rng = np.random.default_rng(1)
    observed = statistic(is_ai)
    null = np.array([statistic(rng.permutation(is_ai)) for _ in range(permutations)])
    top = observed.argmax()
    max_t = (np.sum(null.max(axis=1) >= observed[top]) + 1) / (permutations + 1)
    marginal = ((null >= observed).sum(axis=0) + 1) / (permutations + 1)

    assert adjusted[top] == max_t
    assert adjusted[top] > marginal[top]
    assert np.all(adjusted >= marginal)


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


def test_ordinal_commitment_counts_only_the_qualified_level():
    """El compromiso de pago es 0/1/2 y solo el 2 cuenta; una celda sin mayoría cuenta 0.

    Colapsarlo con bool() contaría los compromisos vagos como calificados, que es
    exactamente la distinción que separa una promesa ejecutable de un "yo veo cómo hago".
    """
    name = "qualified_payment_commitment"
    assert [cell({name: {"value": v}}, name) for v in (0, 1, 2, None)] == [0, 0, 1, 0]


def test_permutation_pvalue_is_never_exactly_zero():
    """(r+1)/(B+1): publicar p = 0,0000 invita a dudar del resto del análisis."""
    matrix = np.vstack([np.ones((25, 4)), np.zeros((25, 4))])
    is_ai = np.array([True] * 25 + [False] * 25)
    adjusted = westfall_young(matrix, is_ai, _rng(), permutations=200)
    assert adjusted.min() > 0
    assert adjusted.min() == 1 / 201
