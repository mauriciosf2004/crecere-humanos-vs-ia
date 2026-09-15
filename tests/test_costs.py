"""Los costos a escala del informe se calculan, no se escriben.

Si alguien cambia un precio en data/reference/costos.json o toca la fórmula, estos tests
fijan el orden de magnitud que el informe le promete a un banco.
"""

import json
import re

import pytest

from src.results import REFERENCE, scale_costs, tiers


def test_tiers_charges_each_unit_at_its_own_tier():
    """Tramos de volumen: las primeras unidades pagan el primer precio, no todas el último."""
    item = {
        "precio": 0.016,
        "tramos": [{"hasta_min": 100, "precio": 0.02}, {"hasta_min": None, "precio": 0.01}],
    }
    assert tiers(item, 50) == pytest.approx(1.0)
    assert tiers(item, 100) == pytest.approx(2.0)
    assert tiers(item, 300) == pytest.approx(2.0 + 2.0)


def test_tiers_without_tiers_is_a_flat_price():
    assert tiers({"precio": 0.003}, 400_000) == pytest.approx(1200)


def test_scale_costs_match_the_published_prices():
    """100.000 llamadas de 4 minutos: el pipeline propio en lote cuesta menos que el comprado."""
    costos = json.loads((REFERENCE / "costos.json").read_text(encoding="utf-8"))
    scale = scale_costs(costos)
    assert scale["propio_lote"] == pytest.approx(1511, abs=5)
    assert scale["propio_estandar"] == pytest.approx(6711, abs=5)
    assert scale["comprada"] == pytest.approx(6000, abs=5)
    assert scale["propio_lote"] < scale["propio_estandar"]
    # El estéreo dobla solo la transcripción, no el resto del pipeline.
    extra = scale["propio_lote_estereo"] - scale["propio_lote"]
    assert extra == pytest.approx(1200, abs=5)


def test_every_scenario_formula_names_a_real_price():
    """Las fórmulas en prosa de costos.json citan identificadores que existen.

    El archivo describe cada escenario con su fórmula además de calcularla en Python. Si
    alguien renombra una partida y no toca la prosa, el documento y el código dejan de decir
    lo mismo sin que nada falle. Esto lo caza.
    """
    costos = json.loads((REFERENCE / "costos.json").read_text(encoding="utf-8"))
    known = {p["id"] for p in costos["partidas"]} | set(costos["supuestos"])
    known |= {f"canales.{k}" for k in costos["supuestos"]["canales"]}
    # Las cantidades derivadas se definen en la propia nota («gib_texto = …»), así que
    # cuentan como conocidas: lo que se persigue aquí es una partida renombrada.
    known |= set(re.findall(r"([a-z_]\w+)\s*=", costos["supuestos"]["nota_formulas"]))
    for scenario in costos["escenarios"]:
        names = set(re.findall(r"[a-z_][a-z0-9_.]{3,}", scenario["formula"]))
        unknown = {n for n in names if n not in known and not n.startswith("tramos")}
        assert not unknown, f"{scenario['id']} cita lo que no existe: {sorted(unknown)}"
