"""Arma data/public/results.json: las cifras del análisis y la prosa que las rodea.

Cada número del informe se lee aquí de effects.json, anchoring.json, agreement.json,
desenlace.json o citas_alertas.json, y se inserta en una frase; ninguno se escribe a mano.
La redacción, en cambio, es fija y descansa en supuestos sobre los datos: que el encuadre
jurídico se sostiene entre gestiones nuevas y que el compromiso de pago no difiere. Esos
supuestos se comprueban antes de escribir. Si el análisis dejara de sostener una frase, el
armado falla en vez de publicarla.
"""

from __future__ import annotations

import json
import re
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from src.stats import audit_sample_size

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "data" / "public"
REFERENCE = ROOT / "data" / "reference"
ALPHA = 0.05
# Supuestos de planificación del control a escala, los mismos que fijan tests/test_stats.py y
# docs/control-de-calidad.md: acierto del instrumento al 85 % y precisión de ±10 pp.
AUDIT_ACCURACY, AUDIT_HALF_WIDTH = 0.85, 0.10
NBSP = " "

# Etiquetas cortas para el gráfico y la tabla. Dicen lo que mide la rúbrica y nada más:
# una versión más vistosa, como "promete limpiar el historial", afirmaría algo no medido.
SHORT = {
    "legal_department_framing": "Se presenta como área de embargos",
    "offer_expiry_claim": "Dice que la oferta vence hoy",
    "situational_legal_pressure": "Pagar evita un proceso legal",
    "credit_benefit_promised": "Ofrece salir de centrales de riesgo",
    "confidentiality_gate": "Confidencialidad o identidad",
    "qualified_payment_commitment": "Compromiso con fecha y monto",
    "quantified_proposal_stated": "Propuesta con cifras",
    "installment_or_partial_offer": "Ofrece cuotas o abono",
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
    # Una cita normativa partida de su número —«Ley / 1328»— es justo lo que el área de
    # cumplimiento va a cotejar, así que el número viaja pegado a lo que nombra.
    value = re.sub(r"\b(Ley|art\.|arts\.|CE|CGP art\.)\s+(?=\d)", rf"\1{NBSP}", value)
    for loose, tight in (
        (" %", f"{NBSP}%"),
        (" pp", f"{NBSP}pp"),
        ("p < ", f"p{NBSP}<{NBSP}"),
        ("p = ", f"p{NBSP}={NBSP}"),
        ("< 0,", f"<{NBSP}0,"),
    ):
        value = value.replace(loose, tight)
    return value


def pct(k: int, n: int) -> str:
    """Porcentaje entero, redondeado con los empates hacia arriba."""
    return f"{int(Decimal(100 * k / n).quantize(Decimal('1'), rounding=ROUND_HALF_UP))} %"


def tiers(item: dict, quantity: float) -> float:
    """Costo por tramos de volumen: cada unidad paga el precio del tramo en el que cae."""
    if "tramos" not in item:
        return quantity * item["precio"]
    total, used = 0.0, 0.0
    for tier in item["tramos"]:
        limit = next((v for k, v in tier.items() if k.startswith("hasta")), None)
        cap = quantity if limit is None else min(quantity, float(limit))
        total += max(0.0, cap - used) * tier["precio"]
        used = cap
        if used >= quantity:
            break
    return total


def scale_costs(costos: dict) -> dict:
    """Costo mensual de cada arquitectura, calculado desde data/reference/costos.json.

    Las fórmulas están documentadas en ese archivo; aquí no se escribe ningún total a mano.
    """
    s = costos["supuestos"]
    price = {p["id"]: p for p in costos["partidas"]}
    calls, minutes = s["llamadas_mes"], s["minutos_por_llamada"]
    gib_text = calls * s["bytes_texto_por_llamada"] / 2**30
    annotations = calls * s["anotadores_por_llamada"]
    tokens_in = (
        s["tokens_rubrica_por_llamada"] + s["tokens_transcripcion_por_llamada"]
    ) * annotations
    tokens_out = s["tokens_salida_por_llamada"] * annotations
    base = (
        tiers(price["dlp_inspeccion"], gib_text)
        + tiers(price["dlp_transformacion"], gib_text)
        + (
            tokens_in * price["gemini_38_flash_lote_entrada_2026"]["precio"]
            + tokens_out * price["gemini_38_flash_lote_salida_2026"]["precio"]
        )
        / 1e6
        + calls
        * minutes
        * s["gib_audio_por_minuto_mono"]
        * price["cloud_storage_estandar"]["precio"]
    )
    return {
        "llamadas_mes": calls,
        "minutos": minutes,
        "propio_lote": base + calls * minutes * price["stt_v2_lote_dinamico"]["precio"],
        "propio_lote_estereo": base
        + calls * minutes * s["canales"]["estereo"] * price["stt_v2_lote_dinamico"]["precio"],
        "propio_estandar": base + tiers(price["stt_v2_estandar"], calls * minutes),
        "comprada": calls * minutes * price["cx_insights_voz_standard"]["precio"],
    }


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
    """La etiqueta del gráfico. Lo tentativo se dice con la palabra, no con un asterisco.

    Antes se codificaba cuatro veces —color, forma, marca hueca y línea discontinua— un
    matiz que cabe en una palabra, y encima obligaba a bajar a una nota al pie para saber
    qué significaba el asterisco.
    """
    return SHORT[item["variable"]] + (" · tentativo" if tentative(item) else "")


def build() -> dict:
    effects = json.loads((PUBLIC / "effects.json").read_text(encoding="utf-8"))
    anchoring = json.loads((PUBLIC / "anchoring.json").read_text(encoding="utf-8"))
    agreement = json.loads((PUBLIC / "agreement.json").read_text(encoding="utf-8"))
    norms = json.loads((REFERENCE / "cumplimiento.json").read_text(encoding="utf-8"))
    disposition = json.loads((PUBLIC / "desenlace.json").read_text(encoding="utf-8"))
    quotes = {q["variable"]: q for q in json.loads((PUBLIC / "citas_alertas.json").read_text())}
    _require(effects["fuente"] == "consensus", "los datos son el consenso del panel")

    contrasts = effects["contrastes"]
    by_name = {item["variable"]: item for item in contrasts}
    context = {item["variable"]: item for item in effects["composicion"]}
    duration, pilot = effects["duracion"], effects["piloto_n_por_brazo"]
    suelo = effects["mde_suelos_pp"]["suelto"]

    legal = by_name["legal_department_framing"]
    expiry = by_name["offer_expiry_claim"]
    threat = by_name["situational_legal_pressure"]
    credit = by_name["credit_benefit_promised"]
    commitment = by_name["qualified_payment_commitment"]
    prior, contact = context["prior_agreement_followup"], context["effective_contact"]
    n = legal["n_ia"]

    nulls = [i for i in contrasts if i["hipotesis"] == "sin diferencia"]
    any_tentative = any(tentative(i) for i in contrasts)

    new_alert = {
        alert["variable"]: next(
            s
            for s in by_name[alert["variable"]]["estratificado"]["estratos"]
            if s["estrato"] == "nuevo"
        )
        for alert in norms["alertas"]
    }
    _require(
        all(by_name[v]["p_ajustado_nuevas"] < ALPHA for v in new_alert),
        "las cuatro alertas se mantienen entre gestiones nuevas",
    )
    guion = agreement["concentracion_guion"]
    scripted = [
        v
        for name, v in guion.items()
        if name != "credit_benefit_promised"
        and v["ia"]["comparten_la_misma_frase"] / v["ia"]["positivos"] >= 0.8
    ]
    _require(
        len(scripted) == 3,
        "las tres conductas de la IA son una misma frase de guion repetida",
    )
    credit_new = new_alert["credit_benefit_promised"]
    any_new = next(iter(new_alert.values()))

    credito_humano = guion["credit_benefit_promised"]["humano"]
    credito = by_name["credit_benefit_promised"]
    estratos = {s["estrato"]: s for s in commitment["estratificado"]["estratos"]}
    nuevo, previo = estratos["nuevo"], estratos["previo"]

    def by_deadline(acciones: list[dict]) -> list[dict]:
        """Las acciones agrupadas por plazo, en el orden en que aparecen: un plan se lee en
        el tiempo, de izquierda a derecha, no como una lista."""
        grupos: list[dict] = []
        for n_accion, a in enumerate(acciones, start=1):
            a = {**a, "n": n_accion}
            if not grupos or grupos[-1]["plazo"] != a["plazo"]:
                grupos.append({"plazo": a["plazo"], "acciones": []})
            grupos[-1]["acciones"].append(a)
        return grupos

    def counts(item: dict, arm: str) -> str:
        """«43 de 50»: el mismo denominador que todo lo demás del informe, a la vista."""
        return f"{item[f'k_{arm}']} de {item[f'n_{arm}']}"

    def fix_for(variable: str) -> str:
        """Editar una línea o formar a un equipo: lo decide cuánto se repite la frase."""
        g = guion[variable]
        arm = "ia" if g["ia"]["positivos"] >= g["humano"]["positivos"] else "humano"
        share = g[arm]["comparten_la_misma_frase"] / g[arm]["positivos"]
        if share >= 0.8:
            return (
                f"{g[arm]['comparten_la_misma_frase']} de {g[arm]['positivos']} son la misma "
                "frase: se edita el guion."
            )
        return (
            f"{g[arm]['positivos']} menciones en "
            f"{g[arm]['positivos'] - g[arm]['comparten_la_misma_frase']} formulaciones: es "
            "formación, no guion."
        )

    alerts_hold = (
        f"Las cuatro se mantienen entre gestiones nuevas (IA {any_new['n_ia']}, humanos "
        f"{any_new['n_humano']}), donde el beneficio crediticio en humanos sube a "
        f"{pct(credit_new['k_humano'], credit_new['n_humano'])}."
    )

    # Conducta ante una dificultad y embudo de la llamada: conteos, nunca tasas ni
    # contrastes. Los denominadores son pequeños —19 y 22— y el pre-registro reserva eso
    # para conteos. Aquí no se afirma ninguna diferencia: se publica lo que se contó.
    ACEPTA = ("acepta_total", "acepta_parcial", "acepta_vago", "acepta_alcance_indeterminado")
    conducta = {}
    for arm in ("ia", "humano"):
        cierre = disposition["distribucion"]["final_disposition"][arm]
        ante = disposition["distribucion"]["difficulty_response"][arm]
        estado = disposition["distribucion"]["debtor_state_at_close"][arm]
        sin_propuesta = cierre.get("no_aplica", 0) + cierre.get("None", 0)
        conducta[arm] = {
            "llega": n - sin_propuesta,
            "acepta": sum(cierre.get(k, 0) for k in ACEPTA),
            "salda": cierre.get("acepta_total", 0),
            "abono": cierre.get("acepta_parcial", 0),
            "dificultad": sum(v for k, v in ante.items() if k not in ("no_aplica", "None")),
            "reconoce": ante.get("reconoce_y_ofrece", 0),
            "insiste": ante.get("insiste_o_presiona", 0),
            "ofrece_sin": ante.get("ofrece_sin_reconocer", 0),
            "otra": ante.get("reconoce_sin_ofrecer", 0),
            "indefinido": cierre.get("acepta_vago", 0)
            + cierre.get("acepta_alcance_indeterminado", 0),
            "colabora": estado.get("cooperativo", 0),
            "incomodo": sum(estado.get(k, 0) for k in ("evasivo", "molesto", "angustiado")),
            "mudo": estado.get("None", 0),
        }
    _require(
        all(c["dificultad"] >= 15 for c in conducta.values()),
        "hay dificultades expresadas en los dos canales para contar",
    )
    _require(
        all(c["colabora"] + c["incomodo"] + c["mudo"] == n for c in conducta.values()),
        "el estado al cierre reparte las 50 llamadas de cada canal sin perder ninguna",
    )
    _require(
        all(
            c["salda"] + c["abono"] + c["indefinido"] == c["acepta"]
            and c["reconoce"] + c["ofrece_sin"] + c["insiste"] + c["otra"] == c["dificultad"]
            for c in conducta.values()
        ),
        "las partes de cada barra del recorrido suman su total",
    )
    _require(
        commitment["k_ia"] <= conducta["ia"]["acepta"]
        and commitment["k_humano"] <= conducta["humano"]["acepta"],
        "todo compromiso con fecha y monto es también una aceptación en la otra rúbrica",
    )

    heard = agreement["resumen"].get("celdas_escuchadas", 0)
    single_pass = agreement["positivos_familia"]["qualified_payment_commitment"]
    family_anchor = anchoring["total"]
    # El colofón va al pie de la página 2, y casi toda esa página sale de la rúbrica de
    # desenlace, que ancla aparte: citar solo el anclaje de la familia avalaba la página
    # equivocada. Se publican las dos rúbricas sumadas, calculadas.
    anclaje_desenlace = disposition["anclaje"]
    context_anchor = anchoring["total_contexto"]
    anclado = (
        family_anchor["anclados"]
        + context_anchor["anclados"]
        + sum(v[arm]["anclados"] for v in anclaje_desenlace.values() for arm in ("ia", "humano"))
    )
    con_cita = (
        family_anchor["positivos"]
        + context_anchor["positivos"]
        + sum(v[arm]["con_valor"] for v in anclaje_desenlace.values() for arm in ("ia", "humano"))
    )
    misma_familia = [r for r, modelo in agreement["panel"].items() if modelo == "opus"]
    _require(
        len(misma_familia) == 2,
        "dos de los tres anotadores comparten familia de modelo",
    )

    # La red de seguridad del informe: si el análisis deja de sostener una de estas frases,
    # el armado falla en vez de publicarla.
    _require(effects["p_global"] < ALPHA, "hay diferencias sustentables")
    for item in (legal, expiry, threat, credit):
        _require(
            matches(item) and not tentative(item),
            f"«{SHORT[item['variable']]}» se sostiene entre gestiones nuevas",
        )
    _require(
        legal["diff_pp"] > 0 and expiry["diff_pp"] > 0 and credit["diff_pp"] < 0,
        "la IA usa más el encuadre jurídico y el vencimiento; los humanos prometen más beneficios",
    )
    _require(not significant(commitment), "no se puede decir qué canal consigue más compromisos")
    _require(
        commitment["p_ajustado_nuevas"] >= ALPHA,
        "el compromiso tampoco difiere entre gestiones nuevas",
    )
    _require(
        single_pass["extraccion"]["humano"] > single_pass["consenso"]["humano"],
        "la pasada única sobrestimaba los compromisos humanos",
    )
    _require(heard > 0, "las celdas dudosas de compromiso se escucharon")
    _require(prior["k_humano"] > prior["k_ia"], "los humanos retoman más acuerdos previos")
    _require(not any(significant(i) for i in nulls), "no se detectó diferencia en las nulas")
    _require(duration["p_mann_whitney"] >= ALPHA, "la diferencia de duración no es concluyente")
    _require(contact["indeterminado_ia"] > 0, "en llamadas de IA no se sabe con quién se habla")

    audit = {
        pop: audit_sample_size(AUDIT_ACCURACY, AUDIT_HALF_WIDTH, population=pop)
        for pop in (1_000, 100_000, 10_000_000)
    }
    _require(audit[100_000] == audit[10_000_000], "el control no crece con el volumen")

    colofon = (
        "Cada respuesta anotada cita una frase textual de la llamada, y se comprobó que exista: "
        f"{anclado} de {con_cita}. Ninguna cifra se escribió a mano; el método está en el "
        "repositorio."
    )

    acciones = [
        {
            "plazo": "Esta semana, sin costo",
            "que": "Editar tres frases del guion de la IA.",
            # El reparto de cada alerta se calcula: "36 de 43" dice más que un porcentaje
            # y no obliga a redondear nada a mano.
            "cifra": (
                f"{len(scripted)} de las {len(norms['alertas'])} alertas de la IA son una "
                "sola frase repetida: "
                + ", ".join(
                    f"{v['ia']['comparten_la_misma_frase']} de {v['ia']['positivos']}"
                    for v in scripted
                )
                + "."
            ),
        },
        {
            "plazo": "Esta semana, sin costo",
            "que": "Confirmar con quién se habla antes de negociar, en los dos canales.",
            "cifra": (
                f"La IA habla con el titular en {counts(contact, 'ia')} llamadas y los humanos "
                f"en {contact['k_humano']}; en {contact['indeterminado_ia']} de la IA no se sabe "
                "quién contesta."
            ),
        },
        {
            "plazo": "Este trimestre",
            "que": "Formar al equipo humano en qué se puede prometer sobre el reporte.",
            "cifra": (
                f"{counts(credito, 'humano')} llamadas humanas lo ofrecen, frente a "
                f"{credito['k_ia']} de la IA, en "
                f"{credito_humano['positivos'] - credito_humano['comparten_la_misma_frase']} "
                "formulaciones distintas: no es guion, es criterio."
            ),
        },
        {
            # La única línea del cierre que sobrevive al mandato del lector: corregido el guion
            # en septiembre, esto es lo que le dice en marzo si volvió. El número es el acierto
            # del instrumento con precisión dada, y casi no depende del volumen.
            "plazo": "Este trimestre",
            # Cabe en cinco líneas para que esta columna no supere a la de 90 días: si la
            # supera, la retícula crece y el informe se va a tres páginas.
            "que": f"Auditar {audit[100_000]} llamadas por periodo.",
            "cifra": (
                f"{audit[1_000]} con 1.000 llamadas al mes, {audit[100_000]} con 100.000: "
                f"±{AUDIT_HALF_WIDTH * 100:.0f} pp sobre el acierto, a cualquier volumen."
            ),
        },
        {
            "plazo": "90 días",
            "que": (
                "Medir la conversión con un piloto de cuentas asignadas al azar dentro de "
                "cada tipo de gestión."
            ),
            "cifra": (
                f"Con {n} por canal solo se ven diferencias de {suelo:.0f} pp; con "
                f"{pilot['10']} cuentas por grupo, de 10. Se decide con el recaudo a 30 días, "
                "no con promesas."
            ),
        },
        {
            "plazo": "90 días",
            "que": "Incluir un tercer grupo: IA sin anuncio legal ni vencimiento.",
            "cifra": (
                "Hoy el anuncio legal y el vencimiento viajan en el mismo guion: no se puede "
                "saber cuánto pesa cada uno."
            ),
        },
    ]

    return {
        "meta": {
            "titulo": "Cobranza con agentes humanos y de IA: qué cambia en la gestión",
            "cliente": "Creceré AI · Prueba técnica",
            "fecha": "Septiembre 2026",
            "autor": "Mauricio Salas",
            "repositorio": "github.com/mauriciosf2004/crecere-humanos-vs-ia",
        },
        # Cuál cobra mejor se dice como rango compatible, no como «no se detectó diferencia»:
        # con esta muestra lo segundo se lee como empate, y el intervalo admite que la IA cierre
        # bastantes menos compromisos. El argumento a favor de la IA que estaba aquí se cayó en
        # la auditoría: se apoyaba en la única fila que el propio gráfico marca como no sostenida.
        "veredicto": (
            "<strong>Sí hay diferencias sustentables, pero dicen cómo cobra cada canal, no cuál "
            "cobra mejor.</strong> Los dos canales no atendieron la misma cartera: "
            f"{prior['k_humano']} de {prior['n_humano']} llamadas humanas retoman un acuerdo "
            "previo y ninguna de la IA."
        ),
        # Una línea, con peso y aire propio. Lleva las dos acciones y su precio, porque una
        # recomendación sin costo es una opinión.
        "recomendacion": (
            "Corregir el guion de los dos canales antes de escalar —hoy, sin costo— y medir la "
            "conversión con un piloto aleatorizado."
        ),
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
            f"Sobre las {n} llamadas de cada canal. Círculo: más en IA · rombo: más en humanos "
            "· gris: no concluyente · la línea es el margen de error del 95 %."
            + (" «Tentativo»: no se sostiene entre gestiones nuevas." if any_tentative else "")
        ),
        "cumplimiento": {
            "rotulo": norms["rotulo"],
            # Pegada al título, al cuerpo de lectura: viaja con la tabla cuando alguien la
            # fotografía, que es como circulan estas cosas.
            "salvedad": norms["salvedad"],
            # La tabla compara 50 contra 50, y los dos brazos no traen la misma cartera. Sin esta
            # línea, la comparación que el banco ve primero es la sucia. La defensa es más fuerte
            # que la salvedad: al restringir a gestiones nuevas, la promesa de beneficio
            # crediticio en humanos no baja, sube.
            "advertencia": alerts_hold,
            "filas": [
                {
                    "conducta": alert["conducta"],
                    "cita": quotes[alert["variable"]]["cita"],
                    "ia": counts(by_name[alert["variable"]], "ia"),
                    "humano": counts(by_name[alert["variable"]], "humano"),
                    "norma": alert["norma_corta"],
                    "accion": alert["accion"],
                    "arreglo": fix_for(alert["variable"]),
                }
                # Por tamaño de la brecha, no por el orden del archivo de normas: es el mismo
                # criterio que las tarjetas y el gráfico, y el que pide un informe de auditoría
                # (los hallazgos se listan por significancia, no por orden de análisis).
                for alert in sorted(
                    norms["alertas"],
                    key=lambda a: abs(by_name[a["variable"]]["diff_pp"]),
                    reverse=True,
                )
            ],
        },
        # Numerados 1 y 2: la pregunta que el cliente hizo va primero, y las alertas de
        # cumplimiento siguen en 3-6. Antes la lista empezaba en «5» y el lector buscaba la
        # página que faltaba.
        "recorrido_lead": (
            f"Las dos carteras no son la misma: {prior['k_humano']} de {prior['n_humano']} "
            "llamadas humanas retoman un acuerdo previo y ninguna de la IA. Con "
            f"{n} llamadas por canal solo se ven las diferencias grandes, y ninguna cifra de "
            "este recorrido es un porcentaje: son llamadas, sobre la misma regla; en cada par "
            "de las leyendas, el primer número es la IA."
        ),
        "recorrido": [
            {
                "titulo": "1 · Hasta dónde llega la conversación",
                "etapas": [
                    {
                        "label": "Contesta\nel titular",
                        "ia": contact["k_ia"],
                        "human": contact["k_humano"],
                    },
                    {
                        "label": "Llega a una\npropuesta",
                        "ia": conducta["ia"]["llega"],
                        "human": conducta["humano"]["llega"],
                    },
                    {
                        "label": "Termina en\naceptación",
                        "ia": conducta["ia"]["acepta"],
                        "human": conducta["humano"]["acepta"],
                        "parts_ia": [
                            conducta["ia"]["salda"],
                            conducta["ia"]["abono"],
                            conducta["ia"]["indefinido"],
                        ],
                        "parts_human": [
                            conducta["humano"]["salda"],
                            conducta["humano"]["abono"],
                            conducta["humano"]["indefinido"],
                        ],
                        "part_labels": [
                            "salda lo discutido",
                            "abono o parcial",
                            "alcance no definido",
                        ],
                    },
                    {
                        "label": "Compromiso con\nfecha y monto",
                        "ia": commitment["k_ia"],
                        "human": commitment["k_humano"],
                    },
                ],
                # La última barra es la que más se malinterpreta: sin esto, cuatro barras humanas
                # más largas se leen como un marcador, que es justo lo que el titular prohíbe.
                # La aritmética es del propio estrato, sin afirmar una causa que no se midió.
                "pie": (
                    f"Aceptación es lo que se dijo, no plata recaudada. De los "
                    f"{commitment['k_humano']} compromisos humanos, {previo['k_humano']} salen de "
                    f"las {previo['n_humano']} llamadas con acuerdo previo, que la IA nunca tuvo; "
                    f"entre gestiones nuevas son {nuevo['k_humano']} de {nuevo['n_humano']} "
                    f"frente a {nuevo['k_ia']} de {nuevo['n_ia']}."
                ),
            },
            {
                "titulo": "2 · Cómo queda el interlocutor al cerrar",
                "etapas": [
                    {
                        "label": "Al colgar",
                        "ia": n,
                        "human": n,
                        "parts_ia": [
                            conducta["ia"]["colabora"],
                            conducta["ia"]["incomodo"],
                            conducta["ia"]["mudo"],
                        ],
                        "parts_human": [
                            conducta["humano"]["colabora"],
                            conducta["humano"]["incomodo"],
                            conducta["humano"]["mudo"],
                        ],
                        "part_labels": [
                            "colabora",
                            "esquivo, molesto o angustiado",
                            "no habla lo suficiente para saberlo",
                        ],
                    }
                ],
                # Sin pie: la leyenda de la barra ya dice «no habla lo suficiente para saberlo
                # 16·5» tres centímetros más arriba, y repetirlo en prosa no añade nada.
                "pie": "",
            },
            {
                "titulo": "3 · Cuando el deudor dice que no puede pagar",
                "etapas": [
                    {
                        "label": "Respuesta\ndel agente",
                        "ia": conducta["ia"]["dificultad"],
                        "human": conducta["humano"]["dificultad"],
                        "parts_ia": [
                            conducta["ia"]["reconoce"],
                            conducta["ia"]["ofrece_sin"],
                            conducta["ia"]["insiste"],
                            conducta["ia"]["otra"],
                        ],
                        "parts_human": [
                            conducta["humano"]["reconoce"],
                            conducta["humano"]["ofrece_sin"],
                            conducta["humano"]["insiste"],
                            conducta["humano"]["otra"],
                        ],
                        "part_labels": [
                            "reconoce y ofrece alternativa",
                            "ofrece sin reconocer",
                            "insiste o presiona",
                            "otra",
                        ],
                    }
                ],
                # El único sitio del informe donde la IA sale mejor, y la regla de publicación
                # congelada lo autoriza así: conteo descriptivo, nunca diferencia medida.
                "pie": (
                    f"Único bloque con otro denominador: {conducta['ia']['dificultad']} y "
                    f"{conducta['humano']['dificultad']} de las {n}. La IA reconoce la dificultad "
                    f"y ofrece alternativa en {conducta['ia']['reconoce']}, los humanos en "
                    f"{conducta['humano']['reconoce']}: es un conteo, no una diferencia medida."
                ),
            },
        ],
        "cierre": by_deadline(acciones),
        "acciones": acciones,
        "colofon": colofon,
    }


def main() -> None:
    results = _typeset(build())
    path = PUBLIC / "results.json"
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{path.relative_to(ROOT)} · {len(results['acciones'])} acciones")


if __name__ == "__main__":
    main()
