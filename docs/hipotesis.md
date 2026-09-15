# Preguntas, hipótesis y decisiones analíticas

El sentido esperado de cada hipótesis se fijó en el código antes de ver la extracción, pero después
de barridos exploratorios sobre las mismas llamadas; este documento lo recoge después. La sección 6
da las fechas y cuenta qué cambió respecto al primer registro. El orden del documento es el
del razonamiento: qué queríamos entender, qué se podía construir y cómo se contrastó.

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

Se evaluaron cuarenta y siete candidatas: ocho forman la familia, tres se conservan como contexto,
una se fundió con otra y treinta y cinco se descartaron. Los motivos están en `docs/decisiones.md`;
el más repetido fue un denominador condicional o una base insuficiente, y el más instructivo, el
constructo ambiguo. Ejemplo real: un primer intento contaba "del área de
embargos y judicializaciones" como amenaza al deudor, cuando es el nombre del departamento en
el guion de presentación. Son cosas distintas y ahora se miden por separado.

## 4. Las hipótesis

Fijadas con signo antes del contraste definitivo. Cuatro son desfavorables a la IA y dos favorables, y dos predicen que **no** habrá diferencia.
Estas dos no confirman nada por sí solas —con esta potencia es fácil no detectar una
diferencia que existe—, pero funcionan como controles negativos: si el instrumento marcara
distinto a los dos brazos por sistema, aparecería una diferencia donde no se esperaba ninguna.

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

**Inferencia por permutación.** Monte Carlo, con 10.000 reordenamientos y semilla fija, sin supuestos
distribucionales. Cada diferencia lleva además su IC de Newcombe y el p de Fisher exacto.

**Dos niveles, en el orden de la pregunta.** Primero un test global sobre el perfil completo de
las ocho variables, que responde "¿existen diferencias?" con un solo p-valor y sin multiplicidad.
Solo si ese test rechaza se desciende a la familia, con Westfall-Young step-down. Westfall-Young controla
por sí mismo el error por familia al 5 %. La compuerta no añade control de error: ordena la
respuesta, y si el perfil conjunto no difiriera evitaría interpretar variables sueltas.

Se eligió Westfall-Young y no Bonferroni ni Holm porque aprovecha la correlación entre
variables, que aquí es alta —varias miden partes del mismo guion—, y lo discreto de los datos
binarios. La ganancia se simuló: frente a Holm sobre los p de Fisher gana potencia incluso con
variables independientes, y algo más con correlación (`docs/decisiones.md`, §6). Se adoptó
sabiendo cuánto compra, no por prestigio.

**Tamaños de efecto con intervalo, no p-valores.** Cada contraste se reporta en puntos
porcentuales con su intervalo de Newcombe. Con esta potencia, un p-valor solo no dice si la
diferencia importa.

Se evaluó y se descartó el contraste de equivalencia (TOST) para los nulos. La razón es
cuantitativa: se simuló la probabilidad de poder declarar equivalencia con n=50 por brazo y es
del **0,3 % con un margen de ±10 puntos** y **0 % con ±5**. Montar el aparato para no poder
concluir nunca es peor que no montarlo; el intervalo de confianza comunica lo mismo sin fingir
rigor.

## 6. Qué cambió respecto al primer registro

El primer registro, del 10 de septiembre (commit `5a7d9f3`), tenía otras cinco hipótesis:

| Primer registro | Qué pasó con ella |
|---|---|
| La IA es más consistente: menor dispersión de conducta | Abandonada: medirla exigía turnos y separar hablantes, y la diarización se descartó |
| El humano obtiene compromisos más concretos | Reformulada como compromiso de pago calificado (H6) |
| La IA cumple mejor el guion de identificación | Reformulada como confidencialidad o verificación de identidad (H5) |
| Ante una objeción, el humano recupera más | Abandonada: condicionada a que aparezca la objeción y dependiente de los turnos |
| La IA no acorta la llamada | Se contrastó con la duración: no hay diferencia |

**Cuándo se fijó cada cosa**, según el historial del repositorio:

| Momento | Commit | Qué había |
|---|---|---|
| 10-sep, 20:30 | `5a7d9f3` | El primer registro, con las cinco hipótesis de arriba |
| 11-sep, antes de las 19:20 | — | Barridos léxicos exploratorios sobre las 100 transcripciones (`docs/variables-descartadas.md`) |
| 11-sep, 19:20–19:27 | — | Extracción de las ocho variables en las 100 llamadas |
| 11-sep, 19:23 | `757057d` | Rúbrica y lista de las ocho variables, cada una con su sentido esperado |
| 11-sep, 19:27 | `b4cb6a4` | Primer contraste |
| 12-sep, 08:52 | `ca26b46` | La tabla H1–H8 entra en este documento, con los mismos sentidos |

El sentido esperado quedó escrito antes de ver cualquier resultado de la extracción, y no se tocó
después; solo «nulo declarado» pasó a llamarse «sin diferencia». Pero se fijó **después de los
barridos léxicos**, que ya habían mostrado, por ejemplo, el encuadre jurídico de la IA. La corrección
de Westfall-Young protege de las ocho comparaciones de la familia, no de esa selección previa.

Una cota conservadora: aunque se corrigiera por Bonferroni sobre las 47 candidatas exploradas
(umbral 0,05 / 47 ≈ 0,001), las cinco diferencias de encuadre y promesa seguirían siendo
significativas, con p de Fisher sin ajustar entre 2·10⁻¹⁹ y 4·10⁻⁴. La prueba de verdad sigue siendo
el piloto que se propone, con datos nuevos.

## 7. Desenlace de la llamada y reacción del interlocutor (exploratorio, congelado antes de anotar)

Añadido el 13 de septiembre, **antes** de que el panel lea una sola llamada con esta rúbrica
(`src/rubric_desenlace.md`, esquema `src/schema_desenlace.json`). Las 8 conductas miden cómo habla
el agente; faltaba cómo termina la llamada, en el lenguaje de un banco, y cómo responde la persona.
La investigación que lo motiva está en `docs/investigacion.md`.

**Qué ya se había visto.** Con el compromiso de pago ya anotado (0, 1 o 2) se miró antes de congelar
esto que «acepta algo» separa más a los brazos que «compromiso con fecha y monto». La variable nueva
no es ciega a ese patrón. Su valor está en distinguir el acuerdo parcial del total y en la reacción
del interlocutor, no en confirmar esa brecha.

**Cortes, fijados ahora:**

| Corte | Definición | Denominador |
|---|---|---|
| Positivo (principal) | `acepta_parcial`, `acepta_total` o `acepta_alcance_indeterminado` | llamadas con desenlace distinto de `no_aplica` y de `null` |
| Positivo amplio (sensibilidad) | lo anterior o `acepta_vago` | el mismo |
| Positivo por llamada | positivo principal | las 50 llamadas del brazo |
| Peso de lo parcial | `acepta_parcial` | llamadas con positivo principal |
| Malestar al cierre | `angustiado` o `molesto` | llamadas con estado distinto de `null` |
| Reconoce y ofrece | `reconoce_y_ofrece` | llamadas con una dificultad expresada |

Cada corte se reporta por brazo con IC de Newcombe, en el total y dentro de las gestiones nuevas
(sin acuerdo previo). No entra a la familia de 8: sin test global ni Westfall-Young. Las
distribuciones completas van como barras descriptivas, sin test por categoría. Si un denominador baja
de 20 en un brazo, solo se publican conteos.

**Validación y regla de publicación, fijadas ahora:**

- **Coherencia.** El positivo principal se compara con el compromiso calificado (nivel 2) de la
  familia, y cada discrepancia se lista.
- **Escucha.** 20 llamadas, 10 por brazo, con semilla fija, estratificadas por desenlace y con
  prioridad a las discrepancias. Se escuchan los últimos 90 segundos sin ver el voto del panel. Se
  reportan el acuerdo exacto y el AC1 de Gwet por brazo, para el corte positivo y para el malestar
  al cierre.
- **Publicación.** Un corte entra al informe solo si su AC1 es de al menos 0,6 en los dos brazos y el
  acuerdo no difiere de forma visible entre brazos. Si no, va a `docs/decisiones.md` como validación
  negativa. La respuesta ante una dificultad solo se valida por anclaje de citas, así que entra como
  conteo descriptivo o se queda en los documentos.
- **Piloto.** Después del piloto de 6 llamadas solo se admiten cambios de redacción, registrados en
  `docs/decisiones.md`; ningún cambio de categorías ni de cortes.

**Resultado (añadido después de anotar las 300).** El positivo salió no concluyente, como se
esperaba aquí. El único corte cuyo intervalo excluye el cero —positivo por llamada, −28 pp— pierde
la diferencia al comparar solo gestiones nuevas (−11 pp [−33, +8]). Ningún corte pasa la regla de
publicación, porque la escucha de las 20 llamadas que da el AC1 no se ha hecho. Todo el detalle,
con la tabla de cortes y la coherencia con la familia, en `docs/decisiones.md` §18.

**Expectativa honesta.** Potencia exacta de Fisher (α = 0,05 bilateral) con una tasa base del 35 %:

| Diferencia real | Total, 50 frente a 50 | Gestiones nuevas, 50 frente a 24 |
|---|---|---|
| 15 pp | 0,27 | 0,20 |
| 20 pp | 0,46 | 0,33 |
| 30 pp | 0,83 | 0,65 |

Lo más probable es que el positivo salga no concluyente. Se dice ahora, antes de ver los datos.
