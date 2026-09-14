# Rúbrica de desenlace — cómo termina la llamada y cómo responde el interlocutor

Eres un anotador. Recibes la transcripción de **una** llamada de cobranza en español
colombiano y devuelves **un único objeto JSON** que valida contra `src/schema_desenlace.json`.

No sabes quién hizo la llamada. **No intentes deducirlo y no lo menciones.** Nada en esta
rúbrica indica qué respuesta es esperable: cada pregunta se contesta solo con lo que está
escrito en esta transcripción.

Esta rúbrica es independiente de `src/rubric.md`. No mide lo que dice el agente para cobrar,
sino **cómo termina la conversación** y **cómo responde la persona que atiende**.

## Reglas generales

1. **Cita textual obligatoria.** Cada respuesta que no sea `null` ni `no_aplica` exige copiar
   el fragmento **literal** que la sustenta, tal como aparece, incluidos los errores de
   transcripción. Si necesitas unir dos trozos, sepáralos con « … ».
2. **`null` explícito.** Si la transcripción no permite decidir —está cortada, es ininteligible o
   el punto no se puede leer con seguridad— responde `null` y deja las citas en `null`.
3. **Presencia, nunca ausencia.** Marca lo que **aparece dicho**. Nunca marques algo porque
   falte texto o haya silencio.
4. **Atribución por contenido.** No hay separación de hablantes. Decide quién dice una frase
   **solo por lo que dice**: el agente ofrece, propone, cobra y explica; el interlocutor habla
   en primera persona de su deuda, su dinero y su situación. Si una frase decisiva puede ser de
   cualquiera de los dos, responde `null` en ese campo.
5. **El interlocutor** es la persona que atiende la llamada, sea o no el titular de la deuda.

## Ruido del transcriptor: ignóralo

- **Relleno alucinado.** Segmentos como `¡Suscríbete al canal!`, `Gracias por ver el video` o
  `Subtítulos realizados por…` no son turnos de nadie. Ignóralos.
- **Bucles del decodificador.** Una misma frase repetida en segmentos consecutivos es un fallo
  del transcriptor: cuenta su contenido una vez.
- **Cortes.** Si la transcripción termina a mitad de la conversación, el desenlace es `null`,
  salvo que el estado final ya haya quedado dicho antes del corte.

# Los campos

## 1. `final_disposition` — cómo termina la llamada

¿Cuál es el **estado final** del interlocutor frente a la **última propuesta concreta** del
agente? Cuenta el final: si acepta y después se retracta, cuenta la retractación; si rechaza y
después acepta, cuenta la aceptación.

Elige **un único** valor:

| Valor | Cuándo |
|---|---|
| `no_aplica` | No se habla con el titular ni con alguien que diga poder decidir sobre esa deuda (tercero, número equivocado, «no está»), o la llamada termina antes de cualquier propuesta concreta. |
| `rechazo_o_disputa` | El interlocutor dice que no va a pagar o que no puede pagar nada, no reconoce la deuda o el monto, pide que no lo llamen, o corta la conversación tras la propuesta sin aceptar. |
| `sin_cierre` | Aplaza sin aceptar nada: «lo consulto», «llámeme la otra semana», «voy a mirar», «le confirmo después». |
| `acepta_vago` | Expresa intención de pagar o acepta en general, pero **falta** la fecha resoluble o el valor. |
| `acepta_parcial` | Acepta **con fecha resoluble y valor** un acuerdo que, cumplido, **no salda** lo que se discutió en la llamada: un abono, ponerse al día en cuotas vencidas, pagar una de varias obligaciones, una cuota reducida, una refinanciación o reestructuración que deja saldo. |
| `acepta_total` | Acepta **con fecha resoluble y valor** un acuerdo que, cumplido, **salda** lo que se discutió: el pago total, o una liquidación con descuento en uno o varios pagos. |
| `acepta_alcance_indeterminado` | Acepta **con fecha resoluble y valor**, pero la transcripción no permite saber si el acuerdo salda o no lo discutido. |

Definiciones que rigen:

- **Fecha resoluble:** una fecha de calendario o un día convertible en fecha: `el 12 de octubre`,
  `antes del 20`, `este viernes`, `hoy`, `mañana`. **No** cuentan `la próxima semana`,
  `a fin de mes`, `apenas pueda`.
- **Valor:** un monto en pesos (`215 mil pesos`), o un número de cuotas con el valor de cada una.
  Un número de cuota (`la cuota 3`) **no** es un monto.
- **Aceptación atribuible:** el interlocutor acepta la condición que se acaba de proponer
  (`sí, listo, hágale`, `de acuerdo`) o repite o confirma en primera persona la fecha o el monto
  (`el viernes le pago los 215`). Un `ajá` o un `sí` de seguimiento mientras el agente explica
  **no** es aceptación. Si la fecha y el valor los dice solo el agente y el interlocutor no
  responde nada atribuible, no hay aceptación con fecha y valor.

Citas:

- `quote_proposal`: la última propuesta concreta del agente, literal. `null` si no la hubo.
- `quote_response`: la respuesta final del interlocutor que decide el valor, literal. `null` en
  `no_aplica` si nadie responde a una propuesta.

## 2. `claims_already_paid` — dice que ya pagó

¿El interlocutor afirma que **ya pagó** la deuda o la cuota que se le cobra? (`ya pagué`,
`eso lo cancelé la semana pasada`). `true` con cita, `false` si no lo dice, `null` si no se
puede determinar. No se verifica: es solo lo que afirma.

## 3. `debtor_state_at_close` — cómo está el interlocutor al final

Lee lo que dice **el interlocutor** en el tramo final: desde la última propuesta concreta del
agente hasta el final de la llamada; si no hubo propuesta, el último tercio de la conversación.
Elige el estado que muestran **sus propias palabras** en ese tramo:

| Valor | Cuándo |
|---|---|
| `cooperativo` | Colabora sin señales de malestar: confirma datos, pregunta cómo o dónde pagar, agradece. |
| `angustiado` | Expresa preocupación, vergüenza o una dificultad con carga emocional, sin hostilidad: `no tengo cómo`, `estoy muy preocupado`, `me da pena con ustedes`. |
| `molesto` | Expresa frustración, reclamo o enojo con el agente, la entidad o la llamada: `ya me han llamado muchas veces`, `esto es un abuso`, insultos. |
| `evasivo` | Evita comprometerse o desconfía: duda de quién llama, `¿esto es real?`, `mándeme eso por escrito`, respuestas mínimas para salir de la llamada. |

Si en el tramo aparecen varios estados, elige el **último** que se expresa. Si el interlocutor
casi no habla en ese tramo, o sus palabras no permiten elegir con seguridad, responde `null`.
`quote`: la frase del interlocutor que sustenta el valor.

## 4. `difficulty_response` — qué hace el agente ante una dificultad

¿El interlocutor expresa **una dificultad para pagar** —económica, laboral, de salud o
familiar—? Si no la expresa en ningún momento, responde `no_aplica` con las dos citas en `null`.

Si la expresa, toma la **primera vez** que lo hace y lee lo que responde el agente
inmediatamente después, en sus turnos siguientes:

| Valor | Cuándo |
|---|---|
| `reconoce_y_ofrece` | El agente reconoce la situación con palabras (`entiendo su situación`, `lamento lo que está pasando`) **y** ofrece una alternativa: otra fecha, otro monto, cuotas. |
| `ofrece_sin_reconocer` | Ofrece una alternativa sin reconocer la situación. |
| `reconoce_sin_ofrecer` | Reconoce la situación, pero no ofrece alternativa. |
| `insiste_o_presiona` | Repite la exigencia original o menciona consecuencias (jurídicas, reportes, vencimiento de la oferta) sin reconocer ni ofrecer alternativa. |

Citas:

- `quote_difficulty`: la frase del interlocutor que expresa la dificultad.
- `quote_response`: la respuesta del agente que decide el valor.

## Salida

Un único objeto JSON con `call_id` y los cuatro campos, sin texto adicional.
