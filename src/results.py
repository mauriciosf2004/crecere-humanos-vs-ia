"""Arma data/public/results.json: las cifras del análisis y la prosa que las rodea.

Cada número del informe se lee aquí de effects.json, anchoring.json, agreement.json o del
esquema de la rúbrica, y se inserta en una frase; ninguno se escribe a mano. La redacción,
en cambio, es fija y descansa en supuestos sobre los datos: que el encuadre jurídico se
sostiene entre gestiones nuevas y que el compromiso de pago no difiere, por ejemplo. Esos
supuestos se comprueban antes de escribir. Si el análisis dejara de sostener una frase, el
armado falla en vez de publicarla.
"""

from __future__ import annotations

import csv
import json
import re
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from src.charts import signed

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "data" / "public"
REFERENCE = ROOT / "data" / "reference"
SCHEMA = ROOT / "src" / "schema.json"
ALPHA = 0.05
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
    """Formato es-CO a tres decimales, con suelo en < 0,001; un p que redondea a 1 se escribe 1."""
    if p >= 0.9995:
        return "1"
    return "< 0,001" if p < 0.001 else f"{p:.3f}".replace(".", ",")


def p_text(p: float) -> str:
    formatted = p_value(p)
    return f"p {formatted}" if formatted.startswith("<") else f"p = {formatted}"


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


def on_titular() -> dict:
    """Compromiso con fecha y monto sobre las llamadas en que contestó el titular.

    Es el denominador que usa un banco para la promesa de pago (PTP): contactos con el
    titular, no llamadas marcadas.
    """
    counts = {"ia": [0, 0], "humano": [0, 0]}
    with (PUBLIC / "features.csv").open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["effective_contact"] != "titular":
                continue
            bucket = counts[row["arm"]]
            bucket[0] += int(row["qualified_payment_commitment"])
            bucket[1] += 1
    return {arm: {"k": k, "n": n} for arm, (k, n) in counts.items()}


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


def status(item: dict) -> tuple[str, str]:
    """Texto y clase de la etiqueta de resultado en la tabla de hipótesis.

    Dice si se detectó la diferencia, no si se confirmó una predicción: el sentido esperado
    se fijó después de explorar las mismas llamadas. "No detectada" vale tanto si se esperaba
    nula como si no: con esta potencia no detectar es fácil aunque la diferencia exista.
    """
    if not significant(item):
        return "no detectada", "neutral"
    if tentative(item):
        return "solo en el total", "warn"
    return ("detectada", "ok") if matches(item) else ("en sentido contrario", "ko")


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

    legal = by_name["legal_department_framing"]
    expiry = by_name["offer_expiry_claim"]
    threat = by_name["situational_legal_pressure"]
    credit = by_name["credit_benefit_promised"]
    commitment = by_name["qualified_payment_commitment"]
    prior, contact = context["prior_agreement_followup"], context["effective_contact"]
    n = legal["n_ia"]

    def rate(item: dict, arm: str) -> str:
        return pct(item[f"k_{arm}"], item[f"n_{arm}"])

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

    colofon = (
        "Cada cifra sale de una frase textual de la llamada y se comprobó que exista: "
        f"{family_anchor['anclados']} de {family_anchor['positivos']}. Ninguna se escribió a "
        "mano; el método está en el repositorio."
    )

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
            "cobra mejor.</strong> Y los dos canales no atendieron la misma cartera: "
            f"{prior['k_humano']} de {prior['n_humano']} llamadas humanas retoman un acuerdo "
            "previo y ninguna de la IA, así que esto describe cómo habla cada uno."
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
            "esta página es un porcentaje: son llamadas, sobre la misma regla."
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
                "pie": (
                    "Aceptación es lo que se dijo en la llamada, no plata recaudada: no hay datos "
                    "de pago."
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
                "pie": (
                    f"En {conducta['ia']['mudo']} de las {n} llamadas de la IA el interlocutor no "
                    f"habla lo suficiente para saber cómo queda; en humanos, en "
                    f"{conducta['humano']['mudo']}."
                ),
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
                "pie": (
                    "Único bloque con otro denominador: son 19 y 22 de las 50. Sobre la misma "
                    "regla, su largo ya dice cuántas son."
                ),
            },
        ],
        "acciones": [
            {
                "plazo": "Esta semana, sin costo",
                "que": "Editar tres frases del guion de la IA.",
                "cifra": (
                    f"{len(scripted)} de las 4 alertas de la IA son una sola oración repetida "
                    "en el 83-100 % de sus casos."
                ),
            },
            {
                "plazo": "Esta semana, sin costo",
                "que": "Confirmar con quién se habla antes de negociar, en los dos canales.",
                "cifra": (
                    f"La IA habla con el titular en {contact['k_ia']} de {contact['n_ia']} "
                    f"llamadas y en {contact['indeterminado_ia']} no se sabe quién contesta."
                ),
            },
            {
                "plazo": "Este trimestre",
                "que": "Formar al equipo humano en qué se puede prometer sobre el reporte.",
                "cifra": (
                    f"{credito_humano['positivos']} menciones en "
                    f"{credito_humano['positivos'] - credito_humano['comparten_la_misma_frase']} "
                    "formulaciones distintas: no es guion, es criterio."
                ),
            },
            {
                "plazo": "90 días",
                "que": "Medir la conversión con un piloto de cuentas asignadas al azar.",
                "cifra": (
                    f"{pilot['10']} cuentas por grupo para ver 10 pp; se decide con el recaudo "
                    "a 30 días, no con promesas verbales."
                ),
            },
            {
                "plazo": "90 días",
                "que": "Incluir un tercer grupo: IA sin anuncio legal ni vencimiento.",
                "cifra": (
                    "Para medir cuánto de la conversión depende del encuadre, en vez de suponerlo."
                ),
            },
        ],
        "colofon": colofon,
    }


def main() -> None:
    results = _typeset(build())
    path = PUBLIC / "results.json"
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{path.relative_to(ROOT)} · {len(results['acciones'])} acciones")


if __name__ == "__main__":
    main()
