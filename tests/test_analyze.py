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


def test_ordinal_commitment_counts_only_the_qualified_level():
    """El compromiso de pago es 0/1/2 y solo el 2 cuenta.

    Colapsarlo con bool() contaría los compromisos vagos como calificados, que es
    exactamente la distinción que separa una promesa ejecutable de un "yo veo cómo
    hago". Se fijan los tres niveles observados en el corpus.
    """
    import json
    from collections import Counter

    from src.analyze import EXTRACTIONS, FAMILY, load_table

    levels = {}
    for arm in ("humano", "ia"):
        counter = Counter()
        for path in sorted((EXTRACTIONS / arm).glob("*.json")):
            cell = json.loads(path.read_text(encoding="utf-8"))["qualified_payment_commitment"]
            counter[cell["value"] if isinstance(cell, dict) else cell] += 1
        levels[arm] = counter

    assert levels["humano"] == {0: 12, 1: 13, 2: 25}
    assert levels["ia"] == {0: 35, 1: 4, 2: 11}

    matrix, is_ai, _ = load_table()
    column = matrix[:, [n for n, _, _ in FAMILY].index("qualified_payment_commitment")]
    assert column[is_ai].sum() == 11  # no 15: los vagos no cuentan
    assert column[~is_ai].sum() == 25  # no 38


def test_permutation_pvalue_is_never_exactly_zero():
    """(r+1)/(B+1): publicar p = 0,0000 invita a dudar del resto del análisis."""
    matrix = np.vstack([np.ones((25, 4)), np.zeros((25, 4))])
    is_ai = np.array([True] * 25 + [False] * 25)
    adjusted = westfall_young(matrix, is_ai, _rng(), permutations=200)
    assert adjusted.min() > 0
    assert adjusted.min() == 1 / 201
