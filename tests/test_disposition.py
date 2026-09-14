"""Los cortes del desenlace y el acuerdo con la escucha deciden qué entra al informe.

Un error en el denominador de un corte o en el AC1 cambiaría una cifra, o dejaría pasar una
variable que no validó, sin dejar rastro.
"""

import pytest

from src.disposition import _cut, gwet_ac1


def _row(arm, disposition):
    return {"arm": arm, "final_disposition": {"value": disposition}}


def test_positive_cut_excludes_calls_without_a_decision():
    """«No aplica» y null salen del denominador; «acepta vago» cuenta en él pero no es positivo."""
    rows = [
        *[_row("ia", "acepta_total")] * 10,
        *[_row("ia", "acepta_vago")] * 10,
        *[_row("ia", "no_aplica")] * 5,
        *[_row("ia", None)] * 5,
        *[_row("humano", "acepta_parcial")] * 15,
        *[_row("humano", "rechazo_o_disputa")] * 5,
    ]
    evaluable = {
        "rechazo_o_disputa",
        "sin_cierre",
        "acepta_vago",
        "acepta_parcial",
        "acepta_total",
        "acepta_alcance_indeterminado",
    }
    positive = {"acepta_parcial", "acepta_total", "acepta_alcance_indeterminado"}
    cut = _cut(rows, "final_disposition", positive, evaluable)
    assert (cut["k_ia"], cut["n_ia"]) == (10, 20)
    assert (cut["k_humano"], cut["n_humano"]) == (15, 20)
    assert cut["diff_pp"] == pytest.approx(-25)


def test_small_denominators_publish_counts_only():
    rows = [*[_row("ia", "acepta_total")] * 5, *[_row("humano", "acepta_total")] * 30]
    cut = _cut(rows, "final_disposition", {"acepta_total"}, {"acepta_total"})
    assert "diff_pp" not in cut


def test_gwet_ac1_is_one_for_perfect_agreement_and_zero_for_chance():
    assert gwet_ac1([True, False, True, False], [True, False, True, False]) == 1.0
    # Mitad de acuerdo con prevalencia 0,5: el acuerdo observado es el esperado por azar.
    assert gwet_ac1([True, True, False, False], [True, False, True, False]) == pytest.approx(0.0)


def test_gwet_ac1_resists_the_kappa_paradox():
    """Con prevalencia extrema, kappa se desploma y AC1 no: por eso se eligió AC1."""
    heard = [True] + [False] * 19
    panel = [False] * 20
    assert gwet_ac1(heard, panel) > 0.9
