"""Arma data/public/results.json: las cifras del análisis y la prosa que las rodea.

Cada número del informe se lee aquí de effects.json, anchoring.json o del esquema de la
rúbrica, y se inserta en una frase; ninguno se escribe a mano. La redacción, en cambio,
es fija y descansa en supuestos sobre los datos: que el encuadre jurídico se sostiene
dentro de cada tipo de gestión y la brecha comercial no, por ejemplo. Esos supuestos se
comprueban antes de escribir. Si el análisis dejara de sostener una frase, el armado
falla en vez de publicarla.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from src.charts import signed

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "data" / "public"
SCHEMA = ROOT / "src" / "schema.json"
ALPHA = 0.05
NBSP = "\u00a0"

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
    """Espacios de no separación donde un salto de línea partiría una cifra.

    «95 %», «p < 0,001» o «p = 0,319» se leen como una unidad, y en un informe impreso
    no deben quedar repartidos entre dos líneas.
    """
    if isinstance(value, dict):
        return {key: _typeset(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_typeset(item) for item in value]
    if not isinstance(value, str):
        return value
    for loose, tight in (
        (" %", f"{NBSP}%"),
        ("p < ", f"p{NBSP}<{NBSP}"),
        ("p = ", f"p{NBSP}={NBSP}"),
        ("< 0,", f"<{NBSP}0,"),
    ):
        value = value.replace(loose, tight)
    return value


def thousands(n: int) -> str:
    """1042 → 1.042: separador de miles es-CO, igual que en los documentos."""
    return f"{n:,}".replace(",", ".")


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
    """¿El resultado coincide con la hipótesis declarada antes de medir?"""
    if item["hipotesis"] == "sin diferencia":
        return not significant(item)
    return significant(item) and (item["diff_pp"] > 0) == item["hipotesis"].startswith("IA")


def composition_sensitive(item: dict) -> bool:
    """Difiere en el contraste, pero no al comparar llamadas del mismo tipo de gestión."""
    p_strat = item["estratificado"]["p_cmh"]
    return significant(item) and (p_strat is None or p_strat >= ALPHA)


def label(item: dict) -> str:
    return SHORT[item["variable"]] + ("*" if composition_sensitive(item) else "")


def status(item: dict) -> tuple[str, str]:
    """Texto y clase de la etiqueta de resultado en la tabla de hipótesis.

    Una diferencia que no se detecta se rotula "no detectada", tanto si se esperaba nula
    como si se esperaba en una dirección: con esta potencia no detectar es fácil aunque la
    diferencia exista. "No coincide" queda para lo que sale en el sentido contrario.
    """
    if not significant(item):
        return "no detectada", "neutral"
    if composition_sensitive(item):
        return "no concluyente", "warn"
    return ("coincide", "ok") if matches(item) else ("no coincide", "ko")


def fraction(k: int, n: int) -> str:
    return f"{k} de {n}"


def build() -> dict:
    effects = json.loads((PUBLIC / "effects.json").read_text(encoding="utf-8"))
    anchoring = json.loads((PUBLIC / "anchoring.json").read_text(encoding="utf-8"))
    agreement = json.loads((PUBLIC / "agreement.json").read_text(encoding="utf-8"))
    questions = len(json.loads(SCHEMA.read_text(encoding="utf-8"))["properties"]) - 1

    contrasts = effects["contrastes"]
    by_name = {item["variable"]: item for item in contrasts}
    context = {item["variable"]: item for item in effects["composicion"]}
    within = {(i["conducta"], i["brazo"]): i for i in effects["exploratorio_intra_brazo"]}
    duration, mde, base = effects["duracion"], effects["mde_pp"], effects["mde_tasa_base"]
    pilot = effects["piloto_n_por_brazo"]

    legal = by_name["legal_department_framing"]
    expiry = by_name["offer_expiry_claim"]
    threat = by_name["situational_legal_pressure"]
    credit = by_name["credit_benefit_promised"]
    commitment = by_name["qualified_payment_commitment"]
    prior, contact = context["prior_agreement_followup"], context["effective_contact"]
    threat_ai = within[("situational_legal_pressure", "ia")]
    expiry_ai = within[("offer_expiry_claim", "ia")]
    robust = [i for i in contrasts if significant(i) and not composition_sensitive(i)]
    nulls = [i for i in contrasts if i["hipotesis"] == "sin diferencia"]
    null_bound = max(max(abs(i["ci_low_pp"]), abs(i["ci_high_pp"])) for i in nulls)
    n = legal["n_ia"]

    def anchored(name: str) -> tuple[int, int]:
        arms = anchoring["por_variable"][name].values()
        return sum(a["anclados"] for a in arms), sum(a["positivos"] for a in arms)

    measured = [i for i in contrasts if anchored(i["variable"])[1] >= 10]
    weakest = min(measured, key=lambda i: anchored(i["variable"])[0] / anchored(i["variable"])[1])
    weak_ok, weak_total = anchored(weakest["variable"])
    family_anchor, context_anchor = anchoring["total"], anchoring["total_contexto"]
    undetermined = prior["indeterminado_ia"] + prior["indeterminado_humano"]

    panel_models = Counter(agreement["panel"].values())
    panel_text = " y ".join(
        f"{'uno' if k == 1 else 'dos' if k == 2 else k} con {model.capitalize()}"
        for model, k in sorted(panel_models.items(), key=lambda x: x[1])
    )
    cells = agreement["resumen"]["celdas"]
    unanimous, total_cells = cells.get("3/3", 0), sum(cells.values())
    single_pass = agreement["positivos_familia"]["qualified_payment_commitment"]
    tentative = any(composition_sensitive(i) for i in contrasts)

    _require(effects["p_global"] < ALPHA, "hay diferencias sustentables")
    for item in (legal, expiry, threat, credit):
        _require(
            matches(item) and not composition_sensitive(item),
            f"«{SHORT[item['variable']]}» se sostiene dentro de cada tipo de gestión",
        )
    _require(not significant(commitment), "la diferencia en compromisos no es concluyente")
    _require(
        single_pass["extraccion"]["humano"] > single_pass["consenso"]["humano"],
        "la pasada única sobrestimaba los compromisos humanos",
    )
    _require(prior["k_humano"] > prior["k_ia"], "los humanos retoman más acuerdos previos")
    _require(not any(significant(i) for i in nulls), "no se detectó diferencia en las nulas")
    _require(duration["p_mann_whitney"] >= ALPHA, "la diferencia de duración no es concluyente")
    _require(
        threat_ai["diff_pp"] > 0 and expiry_ai["diff_pp"] > 0,
        "dentro de la IA, amenaza y vencimiento acompañan a algo más de cierres",
    )

    if undetermined == 1:
        undetermined_note = " Una llamada sin determinar cuenta como gestión nueva."
    elif undetermined:
        undetermined_note = f" {undetermined} llamadas sin determinar cuentan como gestión nueva."
    else:
        undetermined_note = ""

    return {
        "meta": {
            "titulo": "Cobranza con agentes humanos y de IA: qué cambia en la gestión",
            "cliente": "Creceré AI · Prueba técnica",
            "fecha": "Septiembre 2026",
            "autor": "Mauricio Salas",
        },
        "veredicto": (
            "<strong>Sí hay diferencias estadísticamente sustentables, pero dicen cómo cobra "
            "cada canal, no cuál cobra mejor.</strong> La IA se presenta como área jurídica y "
            "afirma que la oferta vence hoy; en las llamadas humanas se prometen beneficios "
            "crediticios. Ambas prácticas merecen revisión de cumplimiento."
        ),
        "kpis": [
            {
                "valor": f"{len(robust)} de {len(contrasts)}",
                "etiqueta": "diferencias se sostienen dentro del mismo tipo de gestión",
            },
            {
                "valor": f"{legal['k_ia']} vs {legal['k_humano']}",
                "etiqueta": f"se presentan como área jurídica (IA vs humano, de {n})",
            },
            {
                "valor": f"{credit['k_ia']} vs {credit['k_humano']}",
                "etiqueta": f"prometen beneficio crediticio (IA vs humano, de {n})",
            },
            {
                "valor": f"{prior['k_ia']} vs {prior['k_humano']}",
                "etiqueta": f"retoman un acuerdo previo (IA vs humano, de {n})",
            },
        ],
        "efectos": [
            {
                "etiqueta": label(item),
                "tentativo": composition_sensitive(item),
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
            "Morado: más en IA · naranja: más en humanos · gris: sin diferencia detectada · "
            "línea: intervalo de confianza del 95 %."
            + (
                " Punto hueco y *: no concluyente al comparar llamadas del mismo tipo de gestión."
                if tentative
                else ""
            )
        ),
        "hallazgos": [
            {
                "claim": (
                    "La IA se presenta como área jurídica o de embargos en "
                    f"{fraction(legal['k_ia'], n)} llamadas; los humanos, en {legal['k_humano']}."
                ),
                "why": "Se mantiene al comparar llamadas del mismo tipo de gestión.",
                "accion": "Revisar ese encuadre con cumplimiento antes de escalar el canal.",
            },
            {
                "claim": (
                    f"La IA afirma que la oferta vence hoy en {fraction(expiry['k_ia'], n)} "
                    f"llamadas; los humanos, en {expiry['k_humano']}."
                ),
                "why": "Crea urgencia, y con estas grabaciones no se sabe si el plazo es real.",
                "accion": "Contrastar cada vencimiento con la matriz de condonaciones.",
            },
            {
                "claim": (
                    f"En {fraction(credit['k_humano'], n)} llamadas humanas se promete un "
                    f"beneficio en el historial crediticio; en la IA, en {credit['k_ia']}."
                ),
                "why": (
                    "Se midió que se ofrezca, no que sea cierto: depende de la entidad, no del "
                    "gestor."
                ),
                "accion": "Incluir qué se promete en el muestreo de calidad de los gestores.",
            },
            {
                "claim": (
                    "La IA plantea un proceso legal si no se paga en "
                    f"{fraction(threat['k_ia'], n)} llamadas; los humanos, en {threat['k_humano']}."
                ),
                "why": "No es el nombre del área: es la consecuencia que se anuncia al deudor.",
                "accion": "Medir en el piloto si retirarla cambia la conversión.",
            },
            {
                "claim": "No se puede decir qué canal consigue más compromisos de pago.",
                "why": (
                    f"Los humanos los obtienen en {commitment['k_humano']} de {n} llamadas y la IA "
                    "en "
                    f"{commitment['k_ia']}: la diferencia no es concluyente, y además "
                    f"{prior['k_humano']} llamadas humanas retomaban un acuerdo ya hecho, frente a "
                    + ("ninguna" if prior["k_ia"] == 0 else str(prior["k_ia"]))
                    + " de la IA."
                ),
                "accion": (
                    f"Asignar cuentas al azar entre canales: unas {pilot['10']} por canal para "
                    "detectar 10 puntos porcentuales."
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
                "; ninguna llamada de IA lo hacía, así que comparar dentro del mismo tipo de "
                "gestión equivale a comparar gestiones nuevas. "
                if prior["k_ia"] == 0
                else f"; la IA, en {prior['k_ia']} llamadas. "
            )
            + "Se detecta por lo dicho en la llamada, no por datos de cartera."
            + f"{undetermined_note} En {contact['indeterminado_ia']} llamadas de IA no se sabe "
            + f"quién contesta ({contact['indeterminado_humano']} "
            + ("humana)." if contact["indeterminado_humano"] == 1 else "humanas).")
        ),
        "palancas": [
            {
                "titulo": "Un piloto con asignación al azar.",
                "detalle": (
                    "La única forma de medir conversión sin que decida el tipo de gestión: desde "
                    "una "
                    f"tasa del {base * 100:.0f} %, detectar 10 puntos exige unas {pilot['10']} "
                    f"cuentas por canal, y 15 puntos, unas {pilot['15']}."
                ),
            },
            {
                "titulo": "Dentro del piloto, una variante de la IA sin presión.",
                "detalle": (
                    "En la IA, las llamadas con amenaza o con vencimiento cierran algo más "
                    f"({threat_ai['k_con']} de {threat_ai['n_con']} frente a "
                    f"{threat_ai['k_sin']} de {threat_ai['n_sin']}; {expiry_ai['k_con']} de "
                    f"{expiry_ai['n_con']} frente a {expiry_ai['k_sin']} de {expiry_ai['n_sin']}): "
                    "es exploratorio y no separa causa de efecto, así que retirarlas hay que "
                    "medirlo."
                ),
            },
        ],
        "metodo": [
            (
                "Dos transcripciones locales (whisper.cpp) por llamada. Tres agentes ciegos "
                f"—{panel_text}— respondieron por separado {questions} preguntas cerradas; cada "
                f"celda es la respuesta de al menos dos, y {thousands(unanimous)} de "
                f"{thousands(total_cells)} fueron "
                f"unánimes. {family_anchor['anclados']} de {family_anchor['positivos']} "
                f"afirmativas y {context_anchor['anclados']} de {context_anchor['positivos']} de "
                "contexto citan frases que existen en las transcripciones."
            ),
            (
                "Una pasada con un solo modelo aceptaba asentimientos vagos: veía "
                f"{single_pass['extraccion']['humano']} compromisos humanos y "
                f"{single_pass['extraccion']['ia']} de IA donde el panel ve "
                f"{single_pass['consenso']['humano']} y {single_pass['consenso']['ia']}."
            ),
            (
                f"Test global por permutación ({p_text(effects['p_global'])}) y Westfall-Young "
                "para "
                "las ocho comparaciones; intervalos de Newcombe al 95 %. En las dos hipótesis de "
                "ausencia de diferencia no se detectó ninguna, sin descartar brechas de hasta "
                f"{signed(null_bound).lstrip('+')} puntos."
            ),
        ],
        "limitaciones": [
            (
                "Los intervalos no se ajustan por las ocho comparaciones y los p-valores sí: uno "
                "puede no tocar el cero sin que la diferencia sea concluyente."
            ),
            (
                "Sin campaña, fecha ni CRM: el compromiso es verbal, no un pago, y no se sabe "
                "cuántas llamadas no conectan."
            ),
            (
                f"Sin identificador de gestor: las {n} humanas pueden venir de pocas personas. "
                f"Tampoco se sabe cómo se eligieron las {2 * n}."
            ),
            (
                "Sin separar hablantes: la diarización fallaba distinto en voz humana y sintética, "
                "así que no hay latencia ni reparto del habla."
            ),
            (
                f"Con {n} llamadas por canal, una diferencia menor a {mde:.0f} puntos porcentuales "
                f"(desde una tasa del {base * 100:.0f} %) probablemente pasaría inadvertida."
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
