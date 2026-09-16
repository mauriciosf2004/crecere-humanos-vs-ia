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


@dataclass(frozen=True)
class Stage:
    """Una etapa del recorrido: cuántas llamadas de cada canal llegan hasta aquí.

    Si lleva `parts`, la barra se subdivide y las partes tienen que sumar el total: así el
    residuo que una tabla deja que el lector sume mal (7 + 2 no son 11) queda dibujado con su
    propio relleno y su propio número.
    """

    label: str
    ia: int
    human: int
    parts_ia: tuple[int, ...] = ()
    parts_human: tuple[int, ...] = ()
    part_labels: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for total, parts in ((self.ia, self.parts_ia), (self.human, self.parts_human)):
            if parts and sum(parts) != total:
                raise ValueError(f"{self.label}: las partes {parts} no suman {total}")


# A 7,2 px sobre 520 unidades caben ~113 caracteres por línea. El límite no es estético:
# un <text> de SVG no parte línea sola, así que lo que sobra se sale del gráfico sin avisar.
CAPTION_CHARS = 110
CAPTION_LINE = 9.5


def wrap(text: str, chars: int = CAPTION_CHARS) -> list[str]:
    """Parte un pie en líneas de como mucho `chars` caracteres, sin cortar palabras."""
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > chars:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    return lines + [line] if line else lines


def recorrido(panels: list[tuple[str, list[Stage], str]], n: int = 50, width: int = 520) -> str:
    """Tres paneles sobre una sola regla de 0 a `n` llamadas, dibujada una vez arriba.

    La regla resuelve los denominadores sin nota al pie, porque elimina la operación que
    permite mentir: no hay ningún eje al que reescalar. Un subgrupo se dibuja con su propio
    largo —quince unidades dentro de una barra de diecinueve, sobre una regla de cincuenta— y
    detrás de cada barra va el marco completo de `n` en gris, para que una barra corta nunca
    se lea como una barra llena. Cada barra lleva el canal escrito al lado y su conteo al
    final: nada depende de una leyenda de color, que fue lo que invirtió la banda anterior.

    Los rellenos son tres y redundantes con el color: sólido, trama a 45° y contorno vacío.
    Una fotocopia mala funde dos grises en una mancha, pero nunca una trama con un plano.
    """
    label_w, tag_w, count_w, pad = 118, 24, 44, 8
    plot_left = label_w + tag_w + pad
    plot_w = width - plot_left - count_w
    unit = plot_w / n
    # Dentro de un panel las etapas van más juntas (gap_stage) que los paneles entre sí
    # (caption_h): así los tres se leen como capítulos del mismo objeto y no como una lista.
    bar_h, gap_ch, gap_stage, title_h, legend_h, caption_h = 11.5, 2.5, 10, 21, 11, 14
    x = lambda calls: plot_left + calls * unit  # noqa: E731

    height = 30 + sum(
        title_h
        + sum(2 * bar_h + gap_ch + gap_stage + (legend_h if s.parts_ia else 0) for s in stages)
        + (caption_h + CAPTION_LINE * (len(wrap(caption)) - 1) if caption else 4)
        + 6
        for _, stages, caption in panels
    )
    out = [
        f'<svg class="recorrido" viewBox="0 0 {width} {height:.0f}" role="img">',
        "<defs>"
        '<pattern id="rc-hatch-ia" patternUnits="userSpaceOnUse" width="5" height="5" '
        'patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="5" class="rc-hatch ia"/>'
        "</pattern>"
        '<pattern id="rc-hatch-human" patternUnits="userSpaceOnUse" width="5" height="5" '
        'patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="5" class="rc-hatch human"/>'
        "</pattern>"
        "</defs>",
    ]

    # La regla, una vez, arriba: 0, mitad y n. Todo lo de abajo se mide contra ella.
    y = 10
    out.append(f'<line class="rc-rule" x1="{x(0):.1f}" y1="{y}" x2="{x(n):.1f}" y2="{y}"/>')
    for calls in (0, n // 2, n):
        out.append(
            f'<line class="rc-rule" x1="{x(calls):.1f}" y1="{y - 3}" '
            f'x2="{x(calls):.1f}" y2="{y + 3}"/>'
        )
        text = f"{calls} llamadas por canal" if calls == n else str(calls)
        anchor = "end" if calls == n else "middle"
        out.append(
            f'<text class="rc-tick" x="{x(calls):.1f}" y="{y - 5}" '
            f'text-anchor="{anchor}">{text}</text>'
        )
    y += 20

    def bar(y0: float, arm: str, total: int, parts: tuple[int, ...], tag: str) -> None:
        out.append(
            f'<rect class="rc-frame" x="{x(0):.1f}" y="{y0:.1f}" '
            f'width="{plot_w:.1f}" height="{bar_h}"/>'
        )
        out.append(
            f'<text class="rc-tag" x="{plot_left - pad:.1f}" y="{y0 + bar_h * 0.78:.1f}" '
            f'text-anchor="end">{tag}</text>'
        )
        if not parts:
            parts = (total,)
        start = 0
        for index, part in enumerate(parts):
            if part <= 0:
                continue
            fill = ("solid", "hatch", "hollow", "dots")[min(index, 3)]
            out.append(
                f'<rect class="rc-bar {arm} {fill}" x="{x(start):.1f}" y="{y0:.1f}" '
                f'width="{part * unit:.1f}" height="{bar_h}"/>'
            )
            start += part
        if total == 0:
            out.append(
                f'<circle class="rc-zero {arm}" cx="{x(0):.1f}" cy="{y0 + bar_h / 2:.1f}" r="2"/>'
            )
        out.append(
            f'<text class="rc-count {arm}" x="{x(n) + 6:.1f}" '
            f'y="{y0 + bar_h * 0.78:.1f}">{total}</text>'
        )

    for title, stages, caption in panels:
        out.append(f'<text class="rc-title" x="0" y="{y + 6:.1f}">{title}</text>')
        y += title_h
        for stage in stages:
            lines = stage.label.split("\n")
            for k, line in enumerate(lines):
                out.append(f'<text class="rc-label" x="0" y="{y + 8 + k * 9.5:.1f}">{line}</text>')
            bar(y, "ia", stage.ia, stage.parts_ia, "IA")
            bar(y + bar_h + gap_ch, "human", stage.human, stage.parts_human, "HUM")
            y += 2 * bar_h + gap_ch
            if stage.parts_ia:
                bits = []
                for k, name in enumerate(stage.part_labels):
                    fill = ("solid", "hatch", "hollow", "dots")[min(k, 3)]
                    bits.append(
                        f'<tspan class="rc-swatch {fill}">■</tspan> {name} '
                        f"{stage.parts_ia[k]}·{stage.parts_human[k]}"
                    )
                out.append(
                    f'<text class="rc-legend" x="{plot_left:.1f}" y="{y + 8:.1f}">'
                    + "   ".join(bits)
                    + "</text>"
                )
                y += legend_h
            y += gap_stage
        if caption:
            lines = wrap(caption)
            for k, line in enumerate(lines):
                out.append(
                    f'<text class="rc-caption" x="0" y="{y + 2 + k * CAPTION_LINE:.1f}">'
                    f"{line}</text>"
                )
            y += caption_h + CAPTION_LINE * (len(lines) - 1)
        else:
            y += 4
        y += 6

    out.append("</svg>")
    return "\n".join(out)
