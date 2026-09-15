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
    return SHORT[item["variable"]] + ("*" if tentative(item) else "")


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
    questions = len(json.loads(SCHEMA.read_text(encoding="utf-8"))["properties"]) - 1
    norms = json.loads((REFERENCE / "cumplimiento.json").read_text(encoding="utf-8"))
    scale = scale_costs(json.loads((REFERENCE / "costos.json").read_text(encoding="utf-8")))
    titular = on_titular()
    _require(effects["fuente"] == "consensus", "los datos son el consenso del panel")

    contrasts = effects["contrastes"]
    by_name = {item["variable"]: item for item in contrasts}
    context = {item["variable"]: item for item in effects["composicion"]}
    duration, mde, pilot = effects["duracion"], effects["mde_pp"], effects["piloto_n_por_brazo"]
    floors = effects["mde_suelos_pp"]

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

    def lead(item: dict) -> str:
        """Quién va arriba y por cuánto: «IA +84 pp». Más claro que un signo para el lector."""
        difference = 100 * (share(item, "ia") - share(item, "humano"))
        return f"{'IA' if difference > 0 else 'humanos'} +{abs(difference):.0f} pp"

    lote, estereo = (int(round(scale[k], -2)) for k in ("propio_lote", "propio_lote_estereo"))
    estandar, comprada = (int(round(scale[k], -2)) for k in ("propio_estandar", "comprada"))
    titular_gap = signed(
        100
        * (
            titular["ia"]["k"] / titular["ia"]["n"]
            - titular["humano"]["k"] / titular["humano"]["n"]
        )
    )
    new_commitment = next(
        s for s in commitment["estratificado"]["estratos"] if s["estrato"] == "nuevo"
    )
    # Las llamadas sin identificar cuentan como «no titular», así que la tasa publicada es el
    # piso; el techo es contarlas todas como titular. Se publican las dos puntas.
    contact_range = {
        arm: (
            f"{pct(contact[f'k_{arm}'], contact[f'n_{arm}']).rstrip(' %')}-"
            f"{pct(contact[f'k_{arm}'] + contact[f'indeterminado_{arm}'], contact[f'n_{arm}'])}"
        )
        for arm in ("ia", "humano")
    }
    # Cota superior del denominador: ninguna llamada sin identificar tiene compromiso, así que
    # contarlas todas como titular es el peor caso para cada brazo.
    ptp_ceiling = {
        arm: pct(titular[arm]["k"], titular[arm]["n"] + contact[f"indeterminado_{arm}"])
        for arm in ("ia", "humano")
    }
    nulls = [i for i in contrasts if i["hipotesis"] == "sin diferencia"]
    any_tentative = any(tentative(i) for i in contrasts)

    # Las cuatro alertas se muestran sobre 50 y 50, y los brazos no traen la misma cartera.
    # La defensa se calcula aquí para que la tabla no quede como la comparación sucia: el
    # crédito no baja al quitar las renegociaciones, sube, que es lo contrario de lo que
    # supondría quien la ataque.
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
    credit_new = new_alert["credit_benefit_promised"]
    any_new = next(iter(new_alert.values()))
    alerts_hold = (
        f"Las cuatro se mantienen entre gestiones nuevas (IA {any_new['n_ia']}, humanos "
        f"{any_new['n_humano']}), donde el beneficio crediticio en humanos sube a "
        f"{pct(credit_new['k_humano'], credit_new['n_humano'])}."
    )

    cells = agreement["resumen"]["celdas"]
    unanimous, total_cells = cells.get("3/3", 0), sum(cells.values())
    literal_rule = sum(agreement["resumen"].get("ajustes_regla_literal", {}).values())
    heard = agreement["resumen"].get("celdas_escuchadas", 0)
    single_pass = agreement["positivos_familia"]["qualified_payment_commitment"]
    family_anchor, context_anchor = anchoring["total"], anchoring["total_contexto"]
    undetermined = prior["indeterminado_ia"] + prior["indeterminado_humano"]

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

    if undetermined == 1:
        undetermined_note = " Una llamada sin determinar cuenta como gestión nueva."
    elif undetermined:
        undetermined_note = f" {undetermined} llamadas sin determinar cuentan como gestión nueva."
    else:
        undetermined_note = ""

    panel_models = ", ".join(model.capitalize() for model in agreement["panel"].values())
    literal_by_arm = agreement["resumen"].get("ajustes_regla_literal", {})
    methods = [
        (
            "Dos transcripciones locales por llamada. Tres anotadores "
            f"({panel_models}) respondieron {questions} preguntas sin saber el canal; vale la "
            "mayoría."
        ),
        (
            f"{thousands(unanimous)} de {thousands(total_cells)} respuestas unánimes; "
            f"{family_anchor['anclados']} de {family_anchor['positivos']} afirmativas y "
            f"{context_anchor['anclados']} de {context_anchor['positivos']} de contexto citan una "
            "frase textual de la llamada."
        ),
        # Los dos brazos, no solo el humano: el conteo de compromisos depende del criterio de
        # anotación, y publicar cómo cambia uno solo se lee como haber elegido el que conviene.
        # Y son las 14 celdas *de compromiso*: sin unanimidad hay 58 en toda la rejilla.
        (
            "Un solo modelo aceptaba asentimientos vagos: contaba "
            f"{single_pass['extraccion']['humano']} y {single_pass['extraccion']['ia']} "
            f"compromisos donde el panel ve {single_pass['consenso']['humano']} y "
            f"{single_pass['consenso']['ia']}. Las {heard} celdas de compromiso sin unanimidad "
            "se escucharon: manda lo oído."
        ),
        # La dirección esperada se fijó mirando estas mismas llamadas. Decirlo y callar la
        # consecuencia deja el flanco abierto; decirlo con la consecuencia lo cierra, porque
        # los cuatro sostenidos superan el umbral incluso sin suponer dirección.
        (
            f"Test global por permutación ({p_text(effects['p_global'])}) y corrección por las "
            f"{len(contrasts)} comparaciones (Westfall-Young). El sentido esperado se fijó "
            "mirando estas mismas llamadas: por eso los hallazgos se juzgan por tamaño de "
            "efecto e intervalo, no por el p-valor."
        ),
    ]
    if literal_rule:
        _require(not literal_by_arm.get("humano"), "la regla literal solo cambió llamadas de IA")
        methods.append(
            f"En {literal_rule} llamadas de IA, la rúbrica («hoy» es fecha) corrigió al panel en "
            "propuesta con cifras."
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
            "cobra mejor.</strong> La IA se apoya en lo jurídico y en la urgencia; los humanos, en "
            "beneficios sobre el historial crediticio. Cuál cobra mejor no se midió: en "
            f"compromisos de pago los datos admiten desde {abs(commitment['ci_low_pp']):.0f} pp "
            f"menos hasta {commitment['ci_high_pp']:.0f} pp más para la IA. "
            "<strong>Decisión:</strong> corregir el guion de los "
            "dos canales antes de escalar, y medir la conversión con un piloto aleatorizado."
        ),
        "kpis": [
            {
                "valor": f"{rate(legal, 'ia')} vs {rate(legal, 'humano')}",
                "etiqueta": f"área jurídica · {lead(legal)}",
                "clase": "",
                "ia_pct": 100 * share(legal, "ia"),
                "humano_pct": 100 * share(legal, "humano"),
            },
            {
                "valor": f"{rate(expiry, 'ia')} vs {rate(expiry, 'humano')}",
                "etiqueta": f"la oferta vence hoy · {lead(expiry)}",
                "clase": "",
                "ia_pct": 100 * share(expiry, "ia"),
                "humano_pct": 100 * share(expiry, "humano"),
            },
            {
                "valor": f"{rate(credit, 'ia')} vs {rate(credit, 'humano')}",
                "etiqueta": f"beneficio crediticio · {lead(credit)}",
                "clase": "neg",
                "ia_pct": 100 * share(credit, "ia"),
                "humano_pct": 100 * share(credit, "humano"),
            },
            {
                "valor": f"{rate(commitment, 'ia')} vs {rate(commitment, 'humano')}",
                # La única tarjeta que lleva intervalo en vez de diferencia puntual: en un nulo
                # el intervalo *es* el hallazgo, y un «+16 pp» suelto invita a leer un empate.
                "etiqueta": (
                    "compromiso de pago · no concluyente "
                    f"({signed(commitment['ci_low_pp'])} a "
                    f"{signed(commitment['ci_high_pp'])} pp)"
                ),
                "clase": "null",
                "ia_pct": 100 * share(commitment, "ia"),
                "humano_pct": 100 * share(commitment, "humano"),
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
            "Azul y círculo: más en IA · ocre y rombo: más en humanos · gris: no concluyente "
            "con esta muestra · línea: margen de error 95 %."
            + (" *Hueco: no se sostiene entre gestiones nuevas." if any_tentative else "")
        ),
        "cumplimiento": {
            "rotulo": norms["rotulo"],
            # La tabla compara 50 contra 50, y los dos brazos no traen la misma cartera. Sin esta
            # línea, la comparación que el banco ve primero es la sucia. La defensa es más fuerte
            # que la salvedad: al restringir a gestiones nuevas, la promesa de beneficio
            # crediticio en humanos no baja, sube.
            "advertencia": norms["advertencia"] + " " + alerts_hold,
            "filas": [
                {
                    "conducta": alert["conducta"],
                    "ia": rate(by_name[alert["variable"]], "ia"),
                    "humano": rate(by_name[alert["variable"]], "humano"),
                    "norma": alert["norma_corta"],
                    "accion": alert["accion"],
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
        "hallazgos": [
            {
                "claim": (
                    "Cuando contesta el titular, la IA cierra compromiso con fecha y monto en "
                    f"{titular['ia']['k']} de {titular['ia']['n']} llamadas "
                    f"({pct(titular['ia']['k'], titular['ia']['n'])}) y los humanos en "
                    f"{titular['humano']['k']} de {titular['humano']['n']} "
                    f"({pct(titular['humano']['k'], titular['humano']['n'])}): "
                    f"{titular_gap} pp, no concluyente."
                ),
                # El denominador excluye las llamadas donde no se sabe quién contesta, y son 9
                # en IA contra 1 en humanos: esa asimetría infla la tasa de la IA. Se publica
                # también el extremo contrario, que es el que un evaluador calcularía solo.
                "why": (
                    "Entre gestiones nuevas, "
                    f"{pct(new_commitment['k_ia'], new_commitment['n_ia'])} y "
                    f"{pct(new_commitment['k_humano'], new_commitment['n_humano'])}. Si las "
                    f"{contact['indeterminado_ia']} llamadas de IA sin identificar fueran del "
                    f"titular, {ptp_ceiling['ia']} y {ptp_ceiling['humano']}: la conclusión no "
                    "cambia."
                ),
                "accion": (
                    f"Medirlo en un piloto: al menos {pilot['10']} cuentas por grupo para detectar "
                    "10 pp."
                ),
            },
            {
                # «Carteras distintas» afirmaba más de lo que el audio puede sostener: con solo
                # la llamada no se distingue la cartera del guion. «Contextos distintos» es lo
                # que el dato aguanta, y para la decisión —no comparar conversión— da igual cuál
                # de las dos causas sea.
                # El contacto con el titular ya va con sus dos denominadores en el hallazgo
                # anterior: repetirlo aquí gastaba una línea de la página 1 sin añadir nada.
                "claim": (
                    f"Contextos distintos: {prior['k_humano']} de {prior['n_humano']} llamadas "
                    "humanas retoman un acuerdo previo y ninguna de la IA."
                ),
                "why": "",
                "accion": "No comparar conversión entre canales sin asignar las cuentas al azar.",
            },
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
            "El acuerdo previo se detecta por lo dicho en la llamada: puede reflejar la cartera "
            "o la conducta."
            + undetermined_note
            + f" En {contact['indeterminado_ia']} llamadas de IA no se sabe quién contesta "
            + f"({contact['indeterminado_humano']} "
            + ("humana)." if contact["indeterminado_humano"] == 1 else "humanas).")
            + f" Duración mediana: {duration['mediana_ia_s']:.0f} s en IA y "
            + f"{duration['mediana_humano_s']:.0f} s en humanos, sin diferencia concluyente "
            + f"({p_text(duration['p_mann_whitney'])})."
        ),
        "kpis_banco": [
            {
                "kpi": "Contacto con el titular",
                # Rango, no punto: las llamadas donde no se sabe quién contesta cuentan como
                # «no titular», y son 9 en IA contra 1 en humanos. El punto solo es el piso.
                "hoy": (f"sí · IA {contact_range['ia']}, humanos {contact_range['humano']}"),
                "piloto": "sí, con los intentos del marcador",
                "produccion": "sí",
            },
            {
                "kpi": "Compromiso con fecha y monto (PTP sobre titular)",
                "hoy": (
                    f"sí · IA {pct(titular['ia']['k'], titular['ia']['n'])}, humanos "
                    f"{pct(titular['humano']['k'], titular['humano']['n'])}"
                ),
                "piloto": "sí",
                "produccion": "sí",
            },
            {
                "kpi": "Promesa cumplida y recaudo a 30 días",
                "hoy": "no: exige datos de pago",
                "piloto": "sí, KPI principal",
                "produccion": "sí",
            },
            {
                "kpi": "Cure rate por tramo de mora",
                "hoy": "no: exige cartera",
                "piloto": "a 90 días",
                "produccion": "sí",
            },
            {
                "kpi": "Costo por peso recuperado",
                "hoy": "no: exige costos y recaudo",
                "piloto": "sí",
                "produccion": "sí",
            },
            {
                "kpi": "Alertas de cumplimiento por canal",
                "hoy": "sí, las cuatro de arriba",
                "piloto": "sí",
                "produccion": "sí, en todas las llamadas",
            },
            {
                "kpi": "Horario y frecuencia de contacto (Ley 2300)",
                "hoy": "no: exige los registros del marcador",
                "piloto": "sí",
                "produccion": "sí",
            },
        ],
        # El precio que encabeza es el de la configuración que este informe declara necesaria
        # —agente y deudor en canales separados—, no el más barato: anclar en el mínimo y luego
        # decir en otra página que ese mínimo no sirve es precio de vitrina.
        "escala": (
            "Medir esto en producción —transcribir, borrar los datos personales, anotar con la "
            f"rúbrica y el tablero— cuesta unos {thousands(estereo)} USD al mes para "
            f"{thousands(scale['llamadas_mes'])} llamadas de {scale['minutos']} minutos, con "
            f"agente y deudor en canales separados, que es lo que exige separar hablantes. Baja a "
            f"{thousands(lote)} en un solo canal y sube a {thousands(comprada)}-"
            f"{thousands(estandar)} con analítica de proveedor o a precio de lista. No incluye "
            "operar ningún canal. Precios oficiales de lista; el detalle, en el repositorio."
        ),
        "palancas": [
            {
                "titulo": "Un piloto con asignación al azar.",
                "detalle": (
                    "Única forma de medir conversión sin que decida la cartera: "
                    f"{pilot['10']} cuentas por grupo para detectar 10 pp (tasa base "
                    f"{pct(round(100 * effects['mde_tasa_base']), 100)}, potencia "
                    f"{pct(round(100 * effects['potencia_plan']), 100)}). Se decide a los 30 días "
                    "con el recaudo de cada cuenta asignada, no con promesas verbales."
                ),
            },
            {
                "titulo": "Un tercer grupo:",
                "detalle": (
                    "IA sin anuncio legal ni vencimiento, para medir su efecto en la conversión "
                    "en vez de suponerlo."
                ),
            },
            {
                "titulo": "Un estándar común.",
                "detalle": (
                    "Ambos canales confirman con quién hablan antes de negociar; los gestores solo "
                    "ofrecen beneficios crediticios que la entidad respalde."
                ),
            },
        ],
        "metodo": methods,
        "limitaciones": [
            (
                "Contactabilidad y resultado final: no hay intentos ni datos de CRM; el "
                "compromiso es verbal, no un pago."
            ),
            "Objeciones y claridad exigen separar hablantes, y ese error favorece a la IA.",
            f"Sin identificador de gestor ni criterio conocido para elegir las {2 * n} llamadas.",
            # El suelo de sensibilidad depende del denominador y de la corrección: publicar solo
            # el del contraste suelto es publicar el más optimista de los tres. El paréntesis
            # anterior mezclaba este umbral con una cota de intervalo, y así leído insinuaba más
            # sensibilidad donde hay menos.
            (
                f"Con {n} llamadas por canal no se detectan diferencias menores a {mde:.0f} pp; "
                f"{floors['titular']:.0f} pp sobre los contactos con titular y "
                f"{floors['familia']:.0f} pp al corregir por las {len(contrasts)} comparaciones."
            ),
        ],
    }


def main() -> None:
    results = _typeset(build())
    path = PUBLIC / "results.json"
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{path.relative_to(ROOT)} · {len(results['hallazgos'])} hallazgos")


if __name__ == "__main__":
    main()
