"""Arma data/public/results.json: las cifras del análisis y la prosa que las rodea.

Cada número del informe se lee aquí de effects.json, anchoring.json, agreement.json o del
esquema de la rúbrica, y se inserta en una frase; ninguno se escribe a mano. La redacción,
en cambio, es fija y descansa en supuestos sobre los datos: que el encuadre jurídico se
sostiene entre gestiones nuevas y que el compromiso de pago no difiere, por ejemplo. Esos
supuestos se comprueban antes de escribir. Si el análisis dejara de sostener una frase, el
armado falla en vez de publicarla.
"""

from __future__ import annotations

import json
from collections import Counter
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from src.charts import signed

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "data" / "public"
SCHEMA = ROOT / "src" / "schema.json"
ALPHA = 0.05
NBSP = " "

# Etiquetas cortas para el gráfico y la tabla. Dicen lo que mide la rúbrica y nada más:
# una versión más vistosa, como "promete limpiar el historial", afirmaría algo no medido.
SHORT = {
    "legal_department_framing": "Se presenta como área jurídica",
    "offer_expiry_claim": "Dice que la oferta vence hoy",
    "situational_legal_pressure": "Plantea un proceso legal",
    "credit_benefit_promised": "Promete beneficio crediticio",
    "confidentiality_gate": "Confidencialidad o identidad",
    "qualified_payment_commitment": "Compromiso con fecha y monto",
    "quantified_proposal_stated": "Propuesta con cifras",
    "installment_or_partial_offer": "Ofrece cuotas o abono",
}

# Las hipótesis se registraron con símbolos; en el informe se leen en palabras.
EXPECTED = {
    "IA ≫ humano": "mucho más en IA",
    "IA > humano": "más en IA",
    "humano ≫ IA": "mucho más en humanos",
    "humano > IA": "más en humanos",
    "sin diferencia": "sin diferencia",
}


def _require(condition: bool, sentence: str) -> None:
    if not condition:
        raise ValueError(f"El análisis ya no sostiene esta frase del informe: {sentence}")


def _typeset(value):
    """Espacios de no separación donde un salto de línea partiría una cifra."""
    if isinstance(value, dict):
        return {key: _typeset(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_typeset(item) for item in value]
    if not isinstance(value, str):
        return value
    for loose, tight in (
        (" %", f"{NBSP}%"),
        (" pp", f"{NBSP}pp"),
        ("p < ", f"p{NBSP}<{NBSP}"),
        ("p = ", f"p{NBSP}={NBSP}"),
        ("< 0,", f"<{NBSP}0,"),
    ):
        value = value.replace(loose, tight)
    return value


def thousands(n: int) -> str:
    """1042 → 1.042: separador de miles es-CO, igual que en los documentos."""
    return f"{n:,}".replace(",", ".")


def pct(k: int, n: int) -> str:
    """Porcentaje entero, redondeado con los empates hacia arriba."""
    return f"{int(Decimal(100 * k / n).quantize(Decimal('1'), rounding=ROUND_HALF_UP))} %"


def interval(item: dict) -> str:
    low, high = signed(item["ci_low_pp"]), signed(item["ci_high_pp"])
    return f"{signed(item['diff_pp'])} [{low}, {high}]"


def p_value(p: float) -> str:
    """Formato es-CO a tres decimales, con suelo en < 0,001."""
    return "< 0,001" if p < 0.001 else f"{p:.3f}".replace(".", ",")


def p_text(p: float) -> str:
    formatted = p_value(p)
    return f"p {formatted}" if formatted.startswith("<") else f"p = {formatted}"


def significant(item: dict) -> bool:
    return item["p_ajustado"] is not None and item["p_ajustado"] < ALPHA


def matches(item: dict) -> bool:
    """¿El resultado coincide con la hipótesis declarada?"""
    if item["hipotesis"] == "sin diferencia":
        return not significant(item)
    return significant(item) and (item["diff_pp"] > 0) == item["hipotesis"].startswith("IA")


def tentative(item: dict) -> bool:
    """Difiere en el contraste, pero no entre gestiones nuevas, corrigiendo por las ocho."""
    return significant(item) and item["p_ajustado_nuevas"] >= ALPHA


def label(item: dict) -> str:
    return SHORT[item["variable"]] + ("*" if tentative(item) else "")


def status(item: dict) -> tuple[str, str]:
    """Texto y clase de la etiqueta de resultado en la tabla de hipótesis.

    Una diferencia que no se detecta se rotula "no detectada", tanto si se esperaba nula
    como si se esperaba en una dirección: con esta potencia no detectar es fácil aunque la
    diferencia exista. "No coincide" queda para lo que sale en el sentido contrario.
    """
    if not significant(item):
        return "no detectada", "neutral"
    if tentative(item):
        return "no concluyente", "warn"
    return ("coincide", "ok") if matches(item) else ("no coincide", "ko")


def build() -> dict:
    effects = json.loads((PUBLIC / "effects.json").read_text(encoding="utf-8"))
    anchoring = json.loads((PUBLIC / "anchoring.json").read_text(encoding="utf-8"))
    agreement = json.loads((PUBLIC / "agreement.json").read_text(encoding="utf-8"))
    questions = len(json.loads(SCHEMA.read_text(encoding="utf-8"))["properties"]) - 1
    _require(effects["fuente"] == "consensus", "los datos son el consenso del panel")

    contrasts = effects["contrastes"]
    by_name = {item["variable"]: item for item in contrasts}
    context = {item["variable"]: item for item in effects["composicion"]}
    duration, mde, pilot = effects["duracion"], effects["mde_pp"], effects["piloto_n_por_brazo"]

    legal = by_name["legal_department_framing"]
    expiry = by_name["offer_expiry_claim"]
    threat = by_name["situational_legal_pressure"]
    credit = by_name["credit_benefit_promised"]
    commitment = by_name["qualified_payment_commitment"]
    prior, contact = context["prior_agreement_followup"], context["effective_contact"]
    n = legal["n_ia"]

    def rate(item: dict, arm: str) -> str:
        return pct(item[f"k_{arm}"], item[f"n_{arm}"])

    def share(item: dict, arm: str) -> float:
        return item[f"k_{arm}"] / item[f"n_{arm}"]

    def points(item: dict) -> str:
        return signed(abs(item["diff_pp"])).lstrip("+")

    new_commitment = next(
        s for s in commitment["estratificado"]["estratos"] if s["estrato"] == "nuevo"
    )
    unanimity = {name: counts.get("3/3", 0) for name, counts in effects["acuerdo_panel"].items()}
    least_unanimous = min((i["variable"] for i in contrasts), key=lambda name: unanimity[name])
    nulls = [i for i in contrasts if i["hipotesis"] == "sin diferencia"]
    null_bound = max(max(abs(i["ci_low_pp"]), abs(i["ci_high_pp"])) for i in nulls)
    any_tentative = any(tentative(i) for i in contrasts)

    panel_models = Counter(agreement["panel"].values())
    panel_text = " y ".join(
        f"{'uno' if k == 1 else 'dos' if k == 2 else k} con {model.capitalize()}"
        for model, k in sorted(panel_models.items(), key=lambda x: x[1])
    )
    cells = agreement["resumen"]["celdas"]
    unanimous, total_cells = cells.get("3/3", 0), sum(cells.values())
    literal_rule = sum(agreement["resumen"].get("ajustes_regla_literal", {}).values())
    single_pass = agreement["positivos_familia"]["qualified_payment_commitment"]
    family_anchor, context_anchor = anchoring["total"], anchoring["total_contexto"]
    undetermined = prior["indeterminado_ia"] + prior["indeterminado_humano"]

    _require(effects["p_global"] < ALPHA, "hay diferencias sustentables")
    for item in (legal, expiry, threat, credit):
        _require(
            matches(item) and not tentative(item),
            f"«{SHORT[item['variable']]}» se sostiene entre gestiones nuevas",
        )
    _require(share(credit, "ia") <= 0.10, "la IA casi no promete beneficios crediticios")
    _require(share(legal, "humano") <= 0.05, "los humanos no se presentan como área jurídica")
    _require(share(expiry, "humano") <= 0.05, "los humanos no usan el vencimiento como presión")
    _require(not significant(commitment), "no se puede decir qué canal consigue más compromisos")
    _require(
        commitment["p_ajustado_nuevas"] >= ALPHA,
        "el compromiso tampoco difiere entre gestiones nuevas",
    )
    _require(
        least_unanimous == "qualified_payment_commitment",
        "el compromiso es la variable donde más discreparon los anotadores",
    )
    _require(
        single_pass["extraccion"]["humano"] > single_pass["consenso"]["humano"],
        "la pasada única sobrestimaba los compromisos humanos",
    )
    _require(prior["k_humano"] > prior["k_ia"], "los humanos retoman más acuerdos previos")
    _require(not any(significant(i) for i in nulls), "no se detectó diferencia en las nulas")
    _require(duration["p_mann_whitney"] >= ALPHA, "la diferencia de duración no es concluyente")

    if undetermined == 1:
        undetermined_note = " Una llamada sin determinar cuenta como gestión nueva."
    elif undetermined:
        undetermined_note = f" {undetermined} llamadas sin determinar cuentan como gestión nueva."
    else:
        undetermined_note = ""

    methods = [
        (
            f"Dos transcripciones locales por llamada. Tres agentes ciegos —{panel_text}— "
            f"respondieron por separado {questions} preguntas cerradas; cada celda es la "
            "respuesta de la mayoría."
        ),
        (
            f"{thousands(unanimous)} de {thousands(total_cells)} celdas con voto unánime; "
            f"{family_anchor['anclados']} de {family_anchor['positivos']} afirmativas y "
            f"{context_anchor['anclados']} de {context_anchor['positivos']} de contexto citan "
            "frases que existen en las transcripciones."
        ),
        (
            "Una pasada con un solo modelo aceptaba asentimientos vagos: veía "
            f"{single_pass['extraccion']['humano']} compromisos humanos donde el panel ve "
            f"{single_pass['consenso']['humano']}."
        ),
        (
            f"Test global por permutación ({p_text(effects['p_global'])}) y corrección de "
            f"Westfall-Young por las {len(contrasts)} comparaciones. Sentido esperado fijado antes "
            "de ver la extracción, tras barridos exploratorios de las mismas llamadas."
        ),
    ]
    if literal_rule:
        methods.append(
            f"En {literal_rule} llamadas se aplicó la rúbrica literal: «hoy» cuenta como fecha "
            "en la propuesta con cifras."
        )

    return {
        "meta": {
            "titulo": "Cobranza con agentes humanos y de IA: qué cambia en la gestión",
            "cliente": "Creceré AI · Prueba técnica",
            "fecha": "Septiembre 2026",
            "autor": "Mauricio Salas",
            "repositorio": "github.com/mauriciosf2004/crecere-humanos-vs-ia",
        },
        "veredicto": (
            "<strong>Sí hay diferencias estadísticamente sustentables, pero dicen cómo cobra "
            "cada canal, no cuál cobra mejor.</strong> Con criterio de cumplimiento, la IA casi no "
            f"promete beneficios crediticios ({rate(credit, 'ia')} frente a "
            f"{rate(credit, 'humano')}); los humanos no se presentan como área jurídica "
            f"({rate(legal, 'humano')} frente a {rate(legal, 'ia')}) ni presionan con el "
            f"vencimiento de la oferta ({rate(expiry, 'humano')} frente a "
            f"{rate(expiry, 'ia')}). En compromisos de pago no hay ganador demostrable."
        ),
        "kpis": [
            {
                "valor": f"{rate(legal, 'ia')} vs {rate(legal, 'humano')}",
                "etiqueta": "área jurídica, IA vs humano",
                "clase": "",
            },
            {
                "valor": f"{rate(expiry, 'ia')} vs {rate(expiry, 'humano')}",
                "etiqueta": "oferta que vence hoy",
                "clase": "",
            },
            {
                "valor": f"{rate(credit, 'ia')} vs {rate(credit, 'humano')}",
                "etiqueta": "promesa de beneficio crediticio",
                "clase": "",
            },
            {
                "valor": f"{rate(commitment, 'ia')} vs {rate(commitment, 'humano')}",
                "etiqueta": "compromiso de pago: no concluyente",
                "clase": "null",
            },
        ],
        "efectos": [
            {
                "etiqueta": label(item),
                "tentativo": tentative(item),
                "significativo": significant(item),
                "diff_pp": item["diff_pp"],
                "ci_low_pp": item["ci_low_pp"],
                "ci_high_pp": item["ci_high_pp"],
                "n_ia": f"{item['k_ia']}/{item['n_ia']}",
                "n_humano": f"{item['k_humano']}/{item['n_humano']}",
            }
            for item in sorted(contrasts, key=lambda i: -abs(i["diff_pp"]))
        ],
        "forest_nota": (
            "Morado: más en IA · naranja: más en humanos · gris: no concluyente tras corregir por "
            f"{len(contrasts)} comparaciones · línea: IC 95 %."
            + (" *Punto hueco: no concluyente entre gestiones nuevas." if any_tentative else "")
            + f" El {rate(prior, 'humano')} de las llamadas humanas retomaba un acuerdo previo"
            + ("; ninguna de IA." if prior["k_ia"] == 0 else f"; de IA, el {rate(prior, 'ia')}.")
        ),
        "hallazgos": [
            {
                "claim": (
                    "La IA se presenta como área jurídica o de embargos en el "
                    f"{rate(legal, 'ia')} de las llamadas, frente al {rate(legal, 'humano')} de "
                    f"los humanos: {points(legal)} pp."
                ),
                "why": "Se mantiene entre gestiones nuevas.",
                "accion": "Revisar ese encuadre con cumplimiento antes de escalar el canal.",
            },
            {
                "claim": (
                    f"La IA dice que la oferta vence hoy en el {rate(expiry, 'ia')} de las "
                    f"llamadas, frente al {rate(expiry, 'humano')} de los humanos: "
                    f"{points(expiry)} pp."
                ),
                "why": "Crea urgencia; las grabaciones no dicen si el plazo es real.",
                "accion": "Contrastar cada vencimiento con la matriz de condonaciones.",
            },
            {
                "claim": (
                    "Los humanos prometen un beneficio en el historial crediticio en el "
                    f"{rate(credit, 'humano')} de las llamadas, frente al {rate(credit, 'ia')} de "
                    f"la IA: {points(credit)} pp."
                ),
                "why": "Se midió que se ofrezca, no que sea cierto.",
                "accion": "Incluir qué se promete en el muestreo de calidad de los gestores.",
            },
            {
                "claim": (
                    "La IA anuncia un proceso legal si no se paga en el "
                    f"{rate(threat, 'ia')} de las llamadas, frente al {rate(threat, 'humano')} de "
                    f"los humanos: {points(threat)} pp."
                ),
                "why": "No es el nombre del área: es la consecuencia que se anuncia.",
                "accion": "Medir en el piloto si retirarla cambia la conversión.",
            },
            {
                "claim": "No se puede decir qué canal consigue más compromisos de pago.",
                "why": (
                    f"Humanos {rate(commitment, 'humano')}, IA {rate(commitment, 'ia')}; entre "
                    "gestiones nuevas, "
                    f"{pct(new_commitment['k_humano'], new_commitment['n_humano'])} y "
                    f"{pct(new_commitment['k_ia'], new_commitment['n_ia'])}. No es concluyente, y "
                    "es la variable en la que más discreparon los anotadores."
                ),
                "accion": (
                    f"Asignar cuentas al azar: al menos {pilot['10']} por canal para detectar "
                    "10 pp."
                ),
            },
        ],
        "tabla": [
            {
                "variable": label(item),
                "esperado": EXPECTED[item["hipotesis"]],
                "ia": f"{item['k_ia']}/{item['n_ia']}",
                "humano": f"{item['k_humano']}/{item['n_humano']}",
                "diff": interval(item),
                "p": p_value(item["p_ajustado"]),
                "estado": status(item)[0],
                "estado_clase": status(item)[1],
            }
            for item in contrasts
        ],
        "composicion": [
            {
                "etiqueta": item["etiqueta"],
                "ia": f"{item['k_ia']}/{item['n_ia']}",
                "humano": f"{item['k_humano']}/{item['n_humano']}",
            }
            for item in effects["composicion"]
        ],
        "composicion_nota": (
            "Los humanos retomaban sobre todo acuerdos ya pactados"
            + (
                "; ninguna llamada de IA lo hacía. "
                if prior["k_ia"] == 0
                else f"; la IA, en {prior['k_ia']} llamadas. "
            )
            + "Se detecta por lo dicho en la llamada, así que puede reflejar tanto la cartera como "
            + "la conducta del agente."
            + undetermined_note
            + f" En {contact['indeterminado_ia']} llamadas de IA no se sabe quién contesta "
            + f"({contact['indeterminado_humano']} "
            + ("humana)." if contact["indeterminado_humano"] == 1 else "humanas).")
        ),
        "palancas": [
            {
                "titulo": "Un piloto con asignación al azar.",
                "detalle": (
                    "Es la única forma de medir conversión sin que decida la cartera: al menos "
                    f"{pilot['10']} cuentas por canal para detectar 10 puntos, y {pilot['15']} "
                    "para 15."
                ),
            },
            {
                "titulo": "Dentro del piloto, una variante de la IA sin amenaza ni vencimiento.",
                "detalle": "Para medir si retirarlos cambia la conversión, en vez de suponerlo.",
            },
        ],
        "metodo": methods,
        "limitaciones": [
            (
                "Contactabilidad y resultado final: no hay intentos ni datos de CRM; el "
                "compromiso es verbal, no un pago."
            ),
            (
                "Objeciones y claridad exigen separar hablantes, y ese error favorecería a la IA; "
                "la negociación se aproxima con propuesta con cifras y cuotas."
            ),
            f"Sin identificador de gestor ni criterio conocido para elegir las {2 * n} llamadas.",
            (
                f"Con {n} llamadas por canal, diferencias menores a {mde:.0f} puntos porcentuales "
                "pueden pasar inadvertidas."
            ),
            (
                f"Hasta {signed(null_bound).lstrip('+')} puntos no se descartan en las variables "
                "donde se esperaba no encontrar diferencia."
            ),
        ],
        "cierre": (
            f"Duración mediana: {duration['mediana_ia_s']:.0f} s en IA y "
            f"{duration['mediana_humano_s']:.0f} s en humanos, sin diferencia concluyente "
            f"({p_text(duration['p_mann_whitney'])})."
        ),
    }


def main() -> None:
    results = _typeset(build())
    path = PUBLIC / "results.json"
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{path.relative_to(ROOT)} · {len(results['hallazgos'])} hallazgos")


if __name__ == "__main__":
    main()
