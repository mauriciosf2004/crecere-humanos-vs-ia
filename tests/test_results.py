"""El informe se arma desde data/public: el mismo insumo debe dar las mismas frases.

results.json está versionado. Si un cambio en results.py altera una cifra o una frase sin
regenerarlo, o si una guarda deja de sostener lo que el informe afirma, este test falla.
"""

import json

from src.results import PUBLIC, _typeset, build


def test_build_reproduces_the_published_results():
    published = json.loads((PUBLIC / "results.json").read_text(encoding="utf-8"))
    assert _typeset(build()) == published
