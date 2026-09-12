# Variables evaluadas y descartadas

La familia contrastada tiene ocho variables. Antes se evaluaron otras treinta y nueve. Esta es la
lista, agrupada por el motivo que las dejó fuera: qué se decidió no medir, y por qué, también es
parte del análisis.

| | |
|---|---|
| Candidatas evaluadas | 47 |
| En la familia contrastada | 8 |
| Conservadas como contexto, sin contraste formal | 3 |
| Fusionada dentro de una variable de la familia | 1 |
| Descartadas | 35 |

Las cifras de este documento salen de la fase de diseño de la rúbrica —barridos sobre las
transcripciones antes de la extracción definitiva— y sirvieron para decidir. No son resultados del
contraste; esos están en `data/public/effects.json`. Las del artefacto de segmentación sí se
recalcularon sobre el corpus final.

## Conservadas como contexto

- **Acuerdo previo.** No es un desenlace: describe la cartera. Se usa para estratificar.
- **Interlocutor** (titular, tercero o indeterminado). Reformula una candidata cuyo tercer nivel, "nadie
  útil", se definía por ausencia de habla; y la ausencia se transcribe distinto en cada brazo.
- **Declaración de automatización.** La comparación es degenerada: un gestor humano no puede
  declararse máquina. Se reporta como cifra descriptiva del canal de IA.

## Fusionada

- **Promesa de retiro de centrales de riesgo.** Era la versión estrecha del mismo acto de habla que
  "promete beneficio en el historial crediticio". Se conservó la amplia; mantener las dos habría
  contado dos veces la misma celda en el test.

## Artefacto de medición (11)

- **Palabras por segmento, variación de la duración de segmento y huecos entre segmentos.** Los
  segmentos del transcriptor no son pausas reales: el 95 % de las fronteras entre segmentos
  humanos y el 95 % de las de IA tienen un hueco de 0 ms, porque whisper tesela la línea de
  tiempo. La tasa de habla por minuto, que no depende de cómo se corten los segmentos, no difiere
  entre brazos (p = 0,46).
- **Latencia de respuesta, reparto del habla, interrupciones, solapamientos, número de turnos y
  densidad de habla.** Todas dependen de saber quién habla, y la separación de hablantes se descartó
  porque su error era distinto en voz humana y sintética (decisión 1).
- **Adherencia a guion por n-gramas repetidos.** Se construía usando la propia etiqueta de brazo, lo
  que invalida contrastarla entre brazos; y la mayoría de sus positivos ya estaban en el encuadre
  jurídico de la presentación.
- **Corte abrupto de la llamada.** El efecto variaba unos 4 puntos según cómo se escribiera el patrón,
  frente a un umbral detectable de 29; y su caso más claro resultó ser un bucle del transcriptor.

## Constructo ambiguo (4)

- **Pregunta por el motivo del impago.** El signo de la diferencia cambiaba según se exigiera que el
  motivo fuera pasado o se aceptara "¿por qué no acepta hoy?".
- **Ruta de pago ejecutable.** Mezclaba nombrar un canal con pedir el soporte de pago, y lo segundo
  es conducta de seguimiento de un acuerdo, no una ruta.
- **Acuerdo afirmado sin aceptación.** Se definía por ausencia y dependía de atribuir un "perfecto"
  suelto sin saber quién lo dice.
- **Pregunta del deudor sin responder.** Juzgar si una respuesta "tiene contenido" es una escala
  subjetiva disfrazada de sí o no.

## Denominador condicional o base insuficiente (16)

- **Revelación de la deuda a un tercero.** Solo definida en seis o siete llamadas por brazo.
- **Respuesta a la primera objeción.** Condicionada a que aparezca una objeción, que ocurre después de
  la conducta del agente que se quería medir.
- **Vía de comprobación ante sospecha de estafa.** Los cuestionamientos de legitimidad resultaron más
  raros en IA que en humanos, justo la dirección contraria a la que la variable necesitaba.
- **El deudor verbaliza que habla con una máquina.** Un caso en cien llamadas. La mejor cita del
  corpus y la peor variable posible.
- **Doce más, sin potencia:** aviso de grabación, anuncio de recontacto, promesa de cese de llamadas,
  verificación estrecha de identidad, entrega de canal de pago, consecuencia patrimonial concreta,
  identificación de la entidad acreedora, bucle de repetición literal, secuencia de captura de datos,
  urgencia genérica, rechazo explícito del deudor y disputa de la deuda. Ninguna superaba 14 puntos
  de diferencia salvo la urgencia genérica, cuyo constructo se apoyaba en muletillas como "pronto".

## Redundancia (4)

- **Cierre binario forzado** ("indíqueme con un sí o un no"). Diferencia de 52 puntos, pero todos sus
  positivos estaban dentro de la oferta con caducidad: no añadía ni una llamada a la familia.
- **Descuento con porcentaje.** Diferencia de 56 puntos, pero contenía por completo a la caducidad de
  la oferta. Se sustituyó por "propuesta con cifras", comercialmente interpretable.
- **Índice de componentes del guion de oferta.** Sus tres componentes coincidían casi siempre
  (Jaccard 0,81): una variable con tres nombres.
- **Pregunta por la capacidad de pago.** Anidada en "ofrece cuotas o abono": añadía una llamada por
  brazo.
