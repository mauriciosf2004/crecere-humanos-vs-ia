"""Gráficos en SVG, emitidos como texto desde Python.

Van inline en el HTML, así que heredan el CSS del documento: el gráfico y la
página son literalmente el mismo sistema visual, y no hay ningún recurso externo
que falle cuando el evaluador abra el adjunto sin conexión.

Hay una sola forma de gráfico porque solo hay una cosa que mostrar: diferencias
con su incertidumbre. Todo lo demás cabe en una frase o en una tabla.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True)
class EffectRow:
    """Una fila del forest plot: un efecto con su intervalo."""

    label: str
    diff_pp: float
    ci_low_pp: float
    ci_high_pp: float
    n_ai: str
    n_human: str
    tentative: bool = False
    significant: bool | None = None  # si se omite, se decide por el intervalo


def signed(value: float) -> str:
    """+80, −28 o 0: entero más cercano con los empates hacia fuera y signo menos tipográfico.

    El redondeo por defecto de Python lleva los empates al par (12,5 da 12), y en un informe
    que alguien va a cotejar contra los datos eso se lee como un error.
    """
    rounded = int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return "0" if rounded == 0 else f"{rounded:+d}".replace("-", "−")


def _x(value: float, lo: float, hi: float, left: float, width: float) -> float:
    return left + (value - lo) / (hi - lo) * width


def forest(rows: list[EffectRow], width: int = 520, row_height: int = 21) -> str:
    """Diferencias en puntos porcentuales con IC95. El cero marcado es la referencia.

    Es el gráfico correcto para esta muestra: muestra la magnitud y la
    incertidumbre a la vez, que es exactamente lo que un p-valor esconde. Las filas
    tentativas —diferencias que no se sostienen al comparar carteras equivalentes—
    llevan punto hueco y línea discontinua, para que no se lean igual de firmes.
    """
    label_width, pad = 210, 16
    plot_left = label_width + pad
    plot_width = width - plot_left - 46
    height = row_height * len(rows) + 34

    span = max(abs(r.ci_low_pp) for r in rows), max(abs(r.ci_high_pp) for r in rows)
    limit = max(max(span), 20)
    limit = min(100, 10 * (int(limit / 10) + 1))
    lo, hi = -limit, limit

    out = [f'<svg class="forest" viewBox="0 0 {width} {height}" role="img">']
    zero = _x(0, lo, hi, plot_left, plot_width)

    # rejilla: solo cero y los extremos. Más líneas no añaden información.
    for value in (lo, 0, hi):
        x = _x(value, lo, hi, plot_left, plot_width)
        cls = "axis-zero" if value == 0 else "axis-tick"
        out.append(f'<line class="{cls}" x1="{x:.1f}" y1="8" x2="{x:.1f}" y2="{height - 26}"/>')
        out.append(f'<text class="axis-label" x="{x:.1f}" y="{height - 12}">{signed(value)}</text>')
    out.append(
        f'<text class="axis-title" x="{zero:.1f}" y="{height - 1}">'
        f"diferencia IA − humano (puntos porcentuales)</text>"
    )

    for index, row in enumerate(rows):
        y = 20 + index * row_height
        x_low = _x(max(row.ci_low_pp, lo), lo, hi, plot_left, plot_width)
        x_high = _x(min(row.ci_high_pp, hi), lo, hi, plot_left, plot_width)
        x_point = _x(row.diff_pp, lo, hi, plot_left, plot_width)
        # El color sigue a la significancia ajustada cuando se conoce: el intervalo es por
        # comparación y puede excluir el cero en una diferencia que, corregida por la
        # familia, no es concluyente. Pintarla de color contradiría a la tabla.
        if row.significant is None:
            detected = not (row.ci_low_pp <= 0 <= row.ci_high_pp)
        else:
            detected = row.significant
        cls = "null" if not detected else ("pos" if row.diff_pp > 0 else "neg")
        mark = " tentative" if row.tentative else ""

        out.append(f'<text class="row-label" x="{label_width}" y="{y + 4}">{row.label}</text>')
        out.append(
            f'<line class="ci {cls}{mark}" x1="{x_low:.1f}" y1="{y}" x2="{x_high:.1f}" y2="{y}"/>'
        )
        out.append(f'<circle class="pt {cls}{mark}" cx="{x_point:.1f}" cy="{y}" r="4"/>')
        out.append(
            f'<text class="row-value {cls}" x="{width - 4}" y="{y + 4}">'
            f"{signed(row.diff_pp)}</text>"
        )

    out.append("</svg>")
    return "\n".join(out)
