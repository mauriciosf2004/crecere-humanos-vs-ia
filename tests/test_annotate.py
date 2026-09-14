"""El voto y la regla literal deciden qué valor entra al análisis en cada celda.

Un error aquí cambiaría datos sin dejar rastro, así que se fijan los casos del voto
—unanimidad, mayoría de dos y empate a tres bandas— y cada condición de la regla.
"""

import pytest

from src.annotate import apply_literal_date_rule, vote

FIELD = "quantified_proposal_stated"
TRANSCRIPT = ["le queda en un pago de 215 mil pesos, vencería hoy mismo si lo confirma"]


def _row(**values):
    return {
        "call_id": "abc",
        "arm": "ia",
        **{k: {"value": v, "quote": None} for k, v in values.items()},
    }


def _claim(quote):
    return {FIELD: {"value": True, "quote": quote}}


def test_unanimous_cell_keeps_value_and_reports_three_of_three():
    consensus = vote([_row(a=True), _row(a=True), _row(a=True)], ["a"])
    assert consensus["a"]["value"] is True
    assert consensus["_acuerdo"]["a"] == "3/3"


def test_two_of_three_wins():
    consensus = vote([_row(a=True), _row(a=False), _row(a=True)], ["a"])
    assert consensus["a"]["value"] is True
    assert consensus["_acuerdo"]["a"] == "2/3"


def test_three_way_split_leaves_the_cell_empty():
    """En el compromiso de pago (0, 1 o 2) los tres pueden discrepar: no se inventa un ganador."""
    consensus = vote([_row(a=0), _row(a=1), _row(a=2)], ["a"])
    assert consensus["a"]["value"] is None
    assert consensus["_acuerdo"]["a"] == "1/3"


def test_literal_date_rule_counts_today_as_a_date():
    """«Vencería hoy mismo» con un monto es propuesta con cifras según la rúbrica escrita."""
    panel = [_row(**{FIELD: False})] * 3
    consensus = vote(panel, [FIELD])
    claim = _claim("un pago de 215 mil pesos, vencería hoy mismo")
    assert apply_literal_date_rule(consensus, [*panel, claim], TRANSCRIPT)
    assert consensus[FIELD]["value"] is True


@pytest.mark.parametrize("quote", ["un pago de 215 mil pesos", "vencería hoy mismo si lo confirma"])
def test_literal_date_rule_needs_an_amount_and_today(quote):
    """Un monto sin «hoy», o «hoy» sin monto, no es propuesta con cifras."""
    panel = [_row(**{FIELD: False})] * 3
    consensus = vote(panel, [FIELD])
    assert not apply_literal_date_rule(consensus, [*panel, _claim(quote)], TRANSCRIPT)
    assert consensus[FIELD]["value"] is False


def test_literal_date_rule_needs_a_quote_that_exists():
    """Una cita que no está en la transcripción no basta para contradecir al panel."""
    panel = [_row(**{FIELD: False})] * 3
    consensus = vote(panel, [FIELD])
    claim = _claim("un pago de 300 mil pesos, vencería hoy mismo")
    assert not apply_literal_date_rule(consensus, [*panel, claim], TRANSCRIPT)
    assert consensus[FIELD]["value"] is False
