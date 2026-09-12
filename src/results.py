"""Arma data/public/results.json: las cifras del análisis y la prosa que las rodea.

Cada número del informe se lee aquí de effects.json o anchoring.json y se inserta
en una frase; ninguno se escribe a mano. La redacción, en cambio, es fija y descansa
en supuestos sobre los datos —que la duración no difiere, que la brecha comercial no
sobrevive a estratificar—. Esos supuestos se comprueban antes de escribir: si el
análisis dejara de sostener una frase, el armado falla en vez de publicarla.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "data" / "public"
ALPHA = 0.05

# Etiquetas cortas para el gráfico y la tabla, donde la frase completa no cabe.
SHORT = {
    "legal_department_framing": "Se presenta desde lo jurídico",
    "offer_expiry_claim": "Dice que la oferta caduca hoy",
    "situational_legal_pressure": "Amenaza con proceso legal",
    "credit_benefit_promised": "Promete limpiar el historial",
    "confidentiality_gate": "Verifica identidad",
    "qualified_payment_commitment": "Compromiso de pago calificado",
    "quantified_proposal_stated": "Propuesta con cifras",
    "installment_or_partial_offer": "Ofrece cuotas o abono",
}


def _require(condition: bool, sentence: str) -> None:
    if not condition:
        raise ValueError(f"El análisis ya no sostiene esta frase del informe: {sentence}")


def signed(value: float) -> str:
    """+80 o −28, con el signo menos tipográfico."""
    return f"{value:+.0f}".replace("-", "−")


def interval(item: dict) -> str:
    low, high = signed(item["ci_low_pp"]), signed(item["ci_high_pp"])
    return f"{signed(item['diff_pp'])} [{low}, {high}]"


def p_value(p: float) -> str:
    """Formato es-CO con tantos decimales como informan: 0,32 · 0,014 · < 0,001."""
    if p < 0.001:
        return "< 0,001"
    return f"{p:.{2 if p >= 0.1 else 3}f}".replace(".", ",")


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
    """Difiere en el contraste, pero deja de ser concluyente al estratificar por cartera."""
    p_strat = item["estratificado"]["p_cmh"]
    return significant(item) and (p_strat is None or p_strat >= ALPHA)


def label(item: dict) -> str:
    return SHORT[item["variable"]] + ("*" if composition_sensitive(item) else "")


def build() -> dict:
    effects = json.loads((PUBLIC / "effects.json").read_text(encoding="utf-8"))
    anchoring = json.loads((PUBLIC / "anchoring.json").read_text(encoding="utf-8"))

    contrasts = effects["contrastes"]
    by_name = {item["variable"]: item for item in contrasts}
    context = {item["variable"]: item for item in effects["composicion"]}
    within = {(i["conducta"], i["brazo"]): i for i in effects["exploratorio_intra_brazo"]}
    duration, mde, anchors = effects["duracion"], effects["mde_pp"], anchoring["total"]

    legal = by_name["legal_department_framing"]
    expiry = by_name["offer_expiry_claim"]
    threat = by_name["situational_legal_pressure"]
    credit = by_name["credit_benefit_promised"]
    commitment = by_name["qualified_payment_commitment"]
    prior, contact = context["prior_agreement_followup"], context["effective_contact"]
    threat_in_ai = within[("situational_legal_pressure", "ia")]
    differing = [item for item in contrasts if significant(item)]
    predicted_nulls = [item for item in contrasts if item["hipotesis"] == "sin diferencia"]
    n = legal["n_ia"]

    _require(effects["p_global"] < ALPHA, "hay diferencias sustentables")
    _require(duration["p_mann_whitney"] >= ALPHA, "la duración no difiere")
    for item in (legal, expiry, threat, credit):
        _require(matches(item), f"{SHORT[item['variable']]} difiere en el sentido declarado")
    _require(composition_sensitive(commitment), "la brecha comercial no es atribuible al agente")
    _require(prior["k_humano"] > prior["k_ia"], "los humanos retoman más acuerdos previos")
    _require(threat_in_ai["p"] >= ALPHA, "la amenaza no se asocia al cierre dentro de la IA")
    _require(all(matches(item) for item in predicted_nulls), "las dos nulas se cumplieron")

    return {
        "meta": {
            "titulo": "Cobranza con agentes humanos y de IA: qué cambia en la gestión",
            "cliente": "Creceré AI · Prueba técnica",
            "fecha": "Septiembre 2026",
            "autor": "Mauricio Salas",
        },
        "veredicto": (
            "<strong>Sí hay diferencias sustentables entre agentes humanos y de IA, y están en "
            "cómo se gestiona, no en cuánto dura la llamada.</strong> La IA encuadra la cobranza "
            "en lo jurídico y presiona con plazos; los gestores humanos prometen limpiar el "
            "historial crediticio. La brecha en compromisos de pago existe, pero no se puede "
            "atribuir al tipo de agente: las dos carteras eran distintas."
        ),
        "kpis": [
            {
                "valor": f"{len(differing)} de {len(contrasts)}",
                "etiqueta": "conductas difieren, con control por comparaciones múltiples",
            },
            {
                "valor": f"{legal['k_ia']} / {legal['k_humano']}",
                "etiqueta": f"abren desde «embargos y judicializaciones» (IA / humano, de {n})",
            },
            {
                "valor": f"{credit['k_ia']} / {credit['k_humano']}",
                "etiqueta": "prometen limpiar el historial crediticio (IA / humano)",
            },
            {
                "valor": f"{prior['k_ia']} / {prior['k_humano']}",
                "etiqueta": "retoman un acuerdo previo (IA / humano): carteras distintas",
            },
        ],
        "efectos": [
            {
                "etiqueta": label(item),
                "diff_pp": item["diff_pp"],
                "ci_low_pp": item["ci_low_pp"],
                "ci_high_pp": item["ci_high_pp"],
                "n_ia": f"{item['k_ia']}/{item['n_ia']}",
                "n_humano": f"{item['k_humano']}/{item['n_humano']}",
            }
            for item in sorted(contrasts, key=lambda i: -abs(i["diff_pp"]))
        ],
        "hallazgos": [
            {
                "claim": (
                    f"La IA abre {legal['k_ia']} de cada {n} llamadas presentándose desde "
                    f"«embargos y judicializaciones»; los humanos, {legal['k_humano']}."
                ),
                "why": "Es la frase del guion de apertura y se mantiene al separar por cartera.",
                "accion": (
                    "Revisar ese encuadre con el área de cumplimiento antes de escalar el canal."
                ),
            },
            {
                "claim": (
                    f"La IA afirma que la oferta caduca hoy en {expiry['k_ia']} de {n} llamadas; "
                    f"los humanos, en {expiry['k_humano']}."
                ),
                "why": "Es urgencia de guion: sale en el mismo bloque que presenta el descuento.",
                "accion": (
                    "Comprobar contra la matriz de condonaciones que el vencimiento sea real."
                ),
            },
            {
                "claim": (
                    f"Los humanos prometen limpiar el historial crediticio en {credit['k_humano']} "
                    f"de {n} llamadas; la IA, en {credit['k_ia']}."
                ),
                "why": (
                    "Es el riesgo que trae el canal humano: una promesa que el gestor no controla."
                ),
                "accion": "Incluirla en el muestreo de calidad de los gestores humanos.",
            },
            {
                "claim": (
                    f"La IA plantea un proceso legal si no se paga en {threat['k_ia']} de {n} "
                    f"llamadas; los humanos, en {threat['k_humano']}."
                ),
                "why": (
                    "Dentro de la propia IA, las llamadas con amenaza no cierran más de forma "
                    f"concluyente ({threat_in_ai['k_con']}/{threat_in_ai['n_con']} frente a "
                    f"{threat_in_ai['k_sin']}/{threat_in_ai['n_sin']}, "
                    f"{p_text(threat_in_ai['p'])})."
                ),
                "accion": "Probar una variante del guion sin amenaza.",
            },
            {
                "claim": (
                    f"Los humanos obtienen compromisos de pago calificados en "
                    f"{commitment['k_humano']} de {n} llamadas; la IA, en {commitment['k_ia']}."
                ),
                "why": (
                    f"No es comparable: {prior['k_humano']} llamadas humanas retomaban un acuerdo "
                    f"ya hecho, frente a {prior['k_ia']} de la IA. Al separar por ese factor la "
                    "diferencia deja de ser concluyente."
                ),
                "accion": "Asignar cuentas al azar entre canales para medir conversión.",
            },
        ],
        "tabla": [
            {
                "variable": label(item),
                "esperado": item["hipotesis"],
                "ia": f"{item['k_ia']}/{item['n_ia']}",
                "humano": f"{item['k_humano']}/{item['n_humano']}",
                "diff": interval(item),
                "p": p_value(item["p_ajustado"]),
                "estado": "coincide" if matches(item) else "no coincide",
                "estado_clase": "ok" if matches(item) else "ko",
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
            "Los humanos retomaban acuerdos ya pactados; la IA abría gestiones nuevas. Al "
            "estratificar por esa diferencia, el encuadre y las promesas se mantienen; lo marcado "
            f"con * deja de ser concluyente. En {contact['indeterminado_ia']} llamadas de IA no se "
            f"puede determinar quién contesta, frente a {contact['indeterminado_humano']} humanas: "
            "esa fila es orientativa."
        ),
        "palancas": [
            {
                "titulo": "Asignar cuentas al azar entre canales.",
                "detalle": (
                    "Es la única forma de medir conversión sin que decida la cartera. Con "
                    f"{n} llamadas por brazo solo se detectan diferencias de {mde:.0f} puntos o "
                    "más."
                ),
            },
            {
                "titulo": "Una variante del guion de IA sin amenaza legal.",
                "detalle": (
                    "Si convierte igual, se retira un riesgo sin coste; hoy no hay evidencia de "
                    "que "
                    "la amenaza compre compromisos."
                ),
            },
            {
                "titulo": "La promesa sobre centrales, al control de calidad humano.",
                "detalle": (
                    f"Aparece en {credit['k_humano']} de {n} llamadas humanas y su cumplimiento "
                    "depende de la fuente, no de quien llama."
                ),
            },
        ],
        "metodo": [
            (
                "Transcripción en local con whisper.cpp: ningún audio salió del equipo. Un modelo "
                "de lenguaje aplicó a cada llamada ocho preguntas cerradas con cita textual "
                f"obligatoria; {anchors['anclados']} de {anchors['positivos']} respuestas "
                "afirmativas citan una frase que existe literalmente en la transcripción."
            ),
            (
                "Contraste en dos niveles: un test global por permutación sobre las ocho conductas "
                f"({p_text(effects['p_global'])}) y, al rechazar, Westfall-Young para saber cuáles "
                "difieren con el error por familia al 5 %. Intervalos de Newcombe."
            ),
            (
                "Las hipótesis se declararon antes de medir, con su signo. Dos predecían que no "
                "habría diferencia, y las dos se cumplieron."
            ),
        ],
        "limitaciones": [
            (
                "Sin campaña, fecha ni resultado de CRM: el compromiso de pago es verbal, no un "
                "pago, y la contactabilidad no se puede medir."
            ),
            (
                "No se separaron hablantes: el error de la diarización era distinto en voz humana "
                "y sintética y habría favorecido a la IA. Por eso no hay métricas de latencia ni "
                "de reparto del habla."
            ),
            f"Con {n} llamadas por brazo, diferencias menores a {mde:.0f} puntos no se distinguen "
            "del ruido.",
        ],
        "cierre": (
            f"La duración tampoco separa a los canales: mediana de "
            f"{duration['mediana_ia_s']:.0f} s en IA y {duration['mediana_humano_s']:.0f} s en "
            f"humanos ({p_text(duration['p_mann_whitney'])}). Lo que cambia entre ellos es qué "
            "se dice, no cuánto se habla."
        ),
    }


def main() -> None:
    results = build()
    path = PUBLIC / "results.json"
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{path.relative_to(ROOT)} · {len(results['hallazgos'])} hallazgos")


if __name__ == "__main__":
    main()
