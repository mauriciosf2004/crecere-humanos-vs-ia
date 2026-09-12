# Preguntas, hipótesis y decisiones analíticas

Registrado antes de medir. El orden importa: primero qué queríamos entender, después qué se
podía construir con lo que había, y solo al final los contrastes.

## 1. Qué queremos entender

La pregunta del encargo es si hay diferencias sustentables entre agentes humanos y de IA. Pero
"desempeño" en cobranza no es una sola cosa, así que la partimos en tres:

- **¿Qué hace cada agente?** — la conducta de la gestión.
- **¿Consigue el objetivo?** — el compromiso de pago.
- **¿Lo consigue de forma defendible ante un banco?** — el encuadre y lo que se promete.

La tercera no estaba en el encargo. La añadimos porque el cliente le vende a bancos, y para un
banco el riesgo de una gestión mal encuadrada pesa más que unos puntos de conversión.

## 2. Qué se podía construir, y qué no

Los audios llegaron sin metadatos: sin campaña, sin fecha, sin identificador de deudor ni de
agente, sin resultado de CRM. Eso cierra de entrada varias puertas y conviene decirlo antes de
enseñar ningún número:

| No se puede medir | Por qué |
|---|---|
| Contactabilidad | Solo hay llamadas conectadas; no hay intentos |
| Horario y frecuencia de contacto (Ley 2300) | Los WAV no traen marca de tiempo |
| Recuperación real, promesas cumplidas | No hay resultado de CRM ni pagos posteriores |
| Diferencias entre gestores humanos | No hay identificador de agente |

Y una limitación de diseño que condiciona todo lo demás: **la asignación de llamadas a cada
brazo no fue aleatoria**, o al menos no hay forma de verificar que lo fuera. Esto es un
cuasi-experimento, no un A/B, y las diferencias pueden deberse a la composición de las carteras.

### La decisión de no separar hablantes

El audio es mono de 8 kHz, así que separar agente de deudor exigía diarización acústica. Se
midió antes de adoptarla y el error resultó **diferencial por brazo**: la voz sintética es
homogénea y sin ruido de fondo, de modo que el algoritmo la separa mejor que a la humana.

Eso descalifica cualquier métrica que dependa de la frontera del turno —reparto del habla,
latencia de respuesta, interrupciones—, porque su error favorecería sistemáticamente al brazo
de IA. Se descartaron las tres. **Todas las variables que quedaron se definen por la presencia
de una frase concreta del agente, ninguna por ausencia**, que es lo que las hace robustas tanto
al error de diarización como a las alucinaciones del transcriptor.

## 3. Las variables

Ocho, binarias, extraídas de la transcripción con cita textual obligatoria. Son a la vez la
rúbrica de anotación y la familia del contraste, y por eso el tamaño está acotado: menos de
seis desaprovecha el diseño, más de doce diluye el test global.

Se evaluaron y descartaron catorce candidatas más. Los motivos están en `docs/decisiones.md`;
el más repetido fue el constructo ambiguo. Ejemplo real: un primer intento contaba "del área de
embargos y judicializaciones" como amenaza al deudor, cuando es el nombre del departamento en
el guion de presentación. Son cosas distintas y ahora se miden por separado.

## 4. Las hipótesis

Declaradas con signo y magnitud antes de medir. Dos apuestan contra la IA, una a su favor, y
dos predicen que **no** habrá diferencia: acertar un nulo previsto es más difícil de conseguir
por azar que encontrar un efecto, y por eso están aquí.

| # | Hipótesis | Esperado |
|---|---|---|
| H1 | La IA encuadra la gestión en lo jurídico desde la presentación | IA ≫ humano |
| H2 | La IA afirma que la oferta caduca | IA ≫ humano |
| H3 | La IA plantea el proceso legal como consecuencia de no pagar | IA ≫ humano |
| H4 | El humano promete beneficios sobre el historial crediticio | humano ≫ IA |
| H5 | La IA verifica identidad o invoca confidencialidad | IA > humano |
| H6 | El humano obtiene más compromisos de pago calificados | humano > IA |
| H7 | Ambos enuncian propuestas con cifras por igual | **sin diferencia** |
| H8 | Ambos ofrecen cuotas o abono parcial por igual | **sin diferencia** |

## 5. Cómo las probamos

La muestra manda sobre el método. Con 50 llamadas por brazo y Fisher exacto, la diferencia
mínima detectable al 80 % de potencia es de **29 puntos porcentuales** (calculada por
enumeración completa de las tablas, no por aproximación normal). Diferencias menores existen
pero esta muestra no las distingue del ruido, y eso se dice en el informe en vez de esconderse.

De ahí salen tres decisiones:

**Inferencia por permutación.** Exacta con este tamaño y sin supuestos distribucionales. Nada
de asintótica.

**Dos niveles, en el orden de la pregunta.** Primero un test global sobre el perfil completo de
las ocho variables, que responde "¿existen diferencias?" con un solo p-valor y sin multiplicidad.
Solo si ese test rechaza se desciende a la familia, con Westfall-Young step-down. Como el primer
nivel actúa de compuerta, el error por familia del procedimiento completo queda en el 5 % sin
corregir nada más.

Se eligió Westfall-Young y no Bonferroni ni Holm porque aprovecha la correlación entre
variables, que aquí es alta —varias miden partes del mismo guion—. La ganancia se simuló antes
de adoptarlo: con variables independientes es idéntico a Holm, y con correlación de 0,7 gana
unos 5 puntos de potencia. Se adoptó sabiendo cuánto compra, no por prestigio.

**Tamaños de efecto con intervalo, no p-valores.** Cada contraste se reporta en puntos
porcentuales con su intervalo de Newcombe. Con esta potencia, un p-valor solo no dice si la
diferencia importa.

Se evaluó y se descartó el contraste de equivalencia (TOST) para los nulos. La razón es
cuantitativa: se simuló la probabilidad de poder declarar equivalencia con n=50 por brazo y es
del **0,3 % con un margen de ±10 puntos** y **0 % con ±5**. Montar el aparato para no poder
concluir nunca es peor que no montarlo; el intervalo de confianza comunica lo mismo sin fingir
rigor.
