"""Gráficos en SVG, emitidos como texto desde Python.

Van inline en el HTML, así que heredan el CSS del documento: el gráfico y la
página son literalmente el mismo sistema visual, y no hay ningún recurso externo
que falle cuando el evaluador abra el adjunto sin conexión.

Una sola forma, porque solo una se gana su espacio: el forest plot muestra magnitud e
incertidumbre a la vez, que es lo que un p-valor esconde. No usa el color como único
código —la dirección va en la forma de la marca—, así que se lee fotocopiado.
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
    significant: bool = False


def signed(value: float) -> str:
    """+80, −28 o 0: entero más cercano con los empates hacia fuera y signo menos tipográfico.

    El redondeo por defecto de Python lleva los empates al par (12,5 da 12), y en un informe
    que alguien va a cotejar contra los datos eso se lee como un error.
    """
    rounded = int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return "0" if rounded == 0 else f"{rounded:+d}".replace("-", "−")


def _x(value: float, lo: float, hi: float, left: float, width: float) -> float:
    return left + (value - lo) / (hi - lo) * width


def _diamond(x: float, y: float, r: float) -> str:
    return (
        f"M {x:.1f} {y - r:.1f} L {x + r:.1f} {y:.1f} L {x:.1f} {y + r:.1f} L {x - r:.1f} {y:.1f} Z"
    )


def forest(rows: list[EffectRow], width: int = 520, row_height: int = 19) -> str:
    """Diferencias en puntos porcentuales con IC 95 %. El cero marcado es la referencia.

    La marca codifica la dirección además del color: círculo cuando la conducta es más
    frecuente en la IA, rombo cuando lo es en los humanos. El matiz de lo tentativo no se
    dibuja: va como palabra en la etiqueta, porque cuatro codificaciones para el mismo
    matiz obligaban a bajar a una nota al pie para descifrar un asterisco.
    """
    # 206 de 520 era el 40 % del ancho para rótulos que no lo necesitan: dejaba 27 mm de
    # papel en blanco a la izquierda y estrechaba el área de trazado.
    label_width, pad = 168, 12
    plot_left = label_width + pad
    plot_width = width - plot_left - 44
    height = row_height * len(rows) + 32

    span = max(abs(r.ci_low_pp) for r in rows), max(abs(r.ci_high_pp) for r in rows)
    limit = max(max(span), 20)
    limit = min(100, 10 * (int(limit / 10) + 1))
    lo, hi = -limit, limit

    out = [f'<svg class="forest" viewBox="0 0 {width} {height}" role="img">']
    zero = _x(0, lo, hi, plot_left, plot_width)

    # Rejilla: solo el cero y los extremos. Más líneas no añaden información.
    for value in (lo, 0, hi):
        x = _x(value, lo, hi, plot_left, plot_width)
        cls = "axis-zero" if value == 0 else "axis-tick"
        out.append(f'<line class="{cls}" x1="{x:.1f}" y1="6" x2="{x:.1f}" y2="{height - 24}"/>')
        out.append(f'<text class="axis-label" x="{x:.1f}" y="{height - 13}">{signed(value)}</text>')
    out.append(
        f'<text class="axis-title" x="{zero:.1f}" y="{height - 2}">'
        f"diferencia IA − humanos, en puntos porcentuales</text>"
    )

    for index, row in enumerate(rows):
        y = 17 + index * row_height
        x_low = _x(max(row.ci_low_pp, lo), lo, hi, plot_left, plot_width)
        x_high = _x(min(row.ci_high_pp, hi), lo, hi, plot_left, plot_width)
        x_point = _x(row.diff_pp, lo, hi, plot_left, plot_width)
        # El color sigue a la significancia ajustada, no al intervalo: el intervalo es por
        # comparación y puede excluir el cero en una diferencia que, corregida por la
        # familia, no es concluyente. Pintarla de color contradiría a la tabla.
        cls = "null" if not row.significant else ("pos" if row.diff_pp > 0 else "neg")

        out.append(f'<text class="row-label" x="{label_width}" y="{y + 3.5}">{row.label}</text>')
        out.append(f'<line class="ci {cls}" x1="{x_low:.1f}" y1="{y}" x2="{x_high:.1f}" y2="{y}"/>')
        if row.diff_pp < 0:
            out.append(f'<path class="pt {cls}" d="{_diamond(x_point, y, 4.2)}"/>')
        else:
            out.append(f'<circle class="pt {cls}" cx="{x_point:.1f}" cy="{y}" r="3.8"/>')
        out.append(
            f'<text class="row-value {cls}" x="{width - 4}" y="{y + 3.5}">'
            f"{signed(row.diff_pp)}</text>"
        )

    out.append("</svg>")
    return "\n".join(out)
