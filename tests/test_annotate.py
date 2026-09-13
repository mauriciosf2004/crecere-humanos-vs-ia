"""El voto decide qué valor entra al análisis en cada celda.

Un error aquí cambiaría datos sin dejar rastro, así que se fijan los tres casos:
unanimidad, mayoría de dos y empate a tres bandas.
"""

from src.annotate import apply_literal_date_rule, vote


def _row(**values):
    return {
        "call_id": "abc",
        "arm": "ia",
        **{k: {"value": v, "quote": None} for k, v in values.items()},
    }


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
    panel = [_row(quantified_proposal_stated=False)] * 3
    original = {
        "quantified_proposal_stated": {
            "value": True,
            "quote": "un pago de 215 mil pesos, vencería hoy mismo",
        }
    }
    consensus = vote(panel, ["quantified_proposal_stated"])
    assert apply_literal_date_rule(consensus, [*panel, original])
    assert consensus["quantified_proposal_stated"]["value"] is True


def test_literal_date_rule_needs_an_amount_and_today():
    """Sin monto no hay propuesta con cifras, aunque la oferta sea por tiempo limitado."""
    panel = [_row(quantified_proposal_stated=False)] * 3
    original = {
        "quantified_proposal_stated": {
            "value": True,
            "quote": "es una propuesta por tiempo limitado",
        }
    }
    consensus = vote(panel, ["quantified_proposal_stated"])
    assert not apply_literal_date_rule(consensus, [*panel, original])
    assert consensus["quantified_proposal_stated"]["value"] is False
