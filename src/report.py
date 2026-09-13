"""Renderiza el informe de dos páginas desde data/public/results.json.

Ningún número se escribe a mano en el HTML: la plantilla solo tiene huecos, y
todo lo que se afirma sale del JSON que produce el análisis. Si una cifra cambia,
cambia en el informe sin que nadie la retipee.
"""

from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from src.charts import EffectRow, forest

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "data" / "public" / "results.json"
TEMPLATE_DIR = ROOT / "report"
OUTPUT = ROOT / "report" / "index.html"


def render() -> Path:
    results = json.loads(RESULTS.read_text(encoding="utf-8"))

    rows = [
        EffectRow(
            label=e["etiqueta"],
            diff_pp=e["diff_pp"],
            ci_low_pp=e["ci_low_pp"],
            ci_high_pp=e["ci_high_pp"],
            n_ai=e["n_ia"],
            n_human=e["n_humano"],
            tentative=e["tentativo"],
            significant=e["significativo"],
        )
        for e in results["efectos"]
    ]

    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        undefined=StrictUndefined,  # una variable que falte rompe el build, no sale en blanco
        autoescape=True,
    )
    html = env.get_template("template.html.j2").render(forest_svg=forest(rows), **results)
    OUTPUT.write_text(html, encoding="utf-8")
    return OUTPUT


def main() -> None:
    path = render()
    print(f"{path.relative_to(ROOT)} · {path.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
