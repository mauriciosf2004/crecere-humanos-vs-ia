# Control de calidad a escala

Este análisis midió 100 llamadas. El producto al que sirve procesa cientos de miles. La
pregunta que decide si el método vale algo no es si acertó aquí, sino **qué cuesta saber que
sigue acertando cuando nadie está mirando**.

La respuesta corta: el control se reparte en cinco capas, cuatro de ellas automáticas y con
cobertura del 100 %, y la única que necesita una persona **no crece con el volumen**.

## El hecho que lo hace posible

La intuición dice que auditar el 20 % de cien llamadas significa auditar el 20 % de cien mil.
Es falso, y la diferencia es el negocio entero.

La precisión con la que se conoce una tasa de acierto depende del **número absoluto** de casos
revisados, no de la fracción del total. La corrección por población finita solo muerde cuando
la muestra es una parte apreciable de la población, y con cien mil llamadas no lo es.
`audit_sample_size` en `src/stats.py` lo calcula; `tests/test_stats.py` lo fija.

| Precisión sobre el acierto | Corpus de 100 | de 1.000 | de 100.000 | de 10 millones |
|---|---|---|---|---|
| ±20 pp | 12 | 13 | 13 | 13 |
| ±10 pp | 34 | 47 | **49** | **49** |
| ±5 pp | 67 | 164 | **196** | **196** |

Multiplicar el corpus por cien mil no cambia la muestra ni en una llamada. Lo que se desploma
es el trabajo relativo: escuchar 49 de 100 es la mitad del corpus; escuchar 49 de 100.000 es el
**0,05 %**. Y la precisión va con la raíz de la muestra, así que exigir el doble de precisión
cuesta el cuádruple de escucha: es la decisión de presupuesto, y conviene tomarla mirando este
número y no a ojo.

## Las cinco capas

### 0 · El esquema cierra la salida · 100 %, costo cero

Cada campo es un conjunto cerrado de valores (`src/schema.json`, `src/schema_desenlace.json`)
y la respuesta del modelo se valida contra él antes de guardarse. Ningún texto libre llega a
una tabla. No es una comprobación de calidad: es una puerta que impide la categoría de error
más tonta y más frecuente.

### 1 · El anclaje de citas · 100 %, automático

Toda respuesta afirmativa obliga a copiar la frase literal que la sostiene, y `src/anchoring.py`
comprueba que esa frase **exista en la transcripción**. Es la capa que importa, porque ataca el
fallo propio de un modelo de lenguaje: inventarse la evidencia.

En este corpus: **258 de 259** afirmativas de la familia y **103 de 103** de contexto quedaron
ancladas. En la segunda rúbrica, 23/24 y 39/40 en desenlace, 34/34 y 45/45 en estado del
interlocutor, 19/19 y 20/22 en respuesta a la dificultad.

Cuesta lo mismo con cien llamadas que con un millón, y se puede convertir en una regla de
producción: *una etiqueta sin cita anclada no entra al tablero*.

### 2 · El panel de tres y su desacuerdo · 100 %, automático

Tres anotadores ciegos, voto de dos sobre tres (`docs/panel-de-anotacion.md`). El voto produce
el dato, pero lo valioso para operar es el subproducto: **el desacuerdo es un medidor de
fragilidad por celda**, gratis y en todas las llamadas.

En este corpus, 1.042 de 1.100 celdas fueron unánimes: el **5,3 %** restante es donde la
medición es frágil. Esa tasa es la señal que se vigila en producción. Si el guion del agente
cambia, si cambia el modelo o si cambia el tipo de cartera, el desacuerdo se mueve **antes** de
que se mueva el resultado.

### 3 · Coherencia entre rúbricas independientes · automático donde dos instrumentos se tocan

Dos rúbricas distintas, congeladas por separado y anotadas por paneles que no se vieron, miden
hechos relacionados. Deben coincidir; donde no coinciden, hay algo que revisar.

Medido: el desenlace positivo frente al compromiso calificado coincide en **48 de 50** llamadas
de IA y **44 de 50** humanas, y las dos rúbricas cuentan **los mismos 9 compromisos de IA**
(`docs/decisiones.md` §18). Ninguna persona intervino en esa comprobación.

Es la capa más barata de añadir y la más ignorada: dos instrumentos que ya existen se validan
mutuamente sin pedirle un minuto a nadie.

### 4 · La escucha humana · muestra fija, costo plano

La última capa y la más pequeña. Sirve para lo que ninguna de las anteriores puede: saber si el
panel entero está **sistemáticamente equivocado**, porque los tres anotadores comparten rúbrica
y dos de ellos comparten familia de modelo, así que comparten sesgos.

Que hace falta no es una hipótesis: cuando se escucharon las 14 celdas de compromiso sin
unanimidad de este corpus, **el oído cambió 8 de 14** (`docs/decisiones.md` §17). Sobre lo
dudoso, el voto de tres modelos no basta.

Cómo se opera sin que crezca:

- **Tamaño fijo por período**, no fracción. Con 50 llamadas al mes se conoce el acierto con
  ±10 pp, con cualquier volumen.
- **Muestreo estratificado, no aleatorio simple.** Escuchar al azar gasta la mayoría de los
  minutos en llamadas donde los tres anotadores coincidieron y no había nada que aprender. La
  muestra se reparte entre celdas en desacuerdo, positivos de conductas raras —los que sostienen
  la dirección de un efecto— y un estrato de control tomado al azar, que es el que detecta el
  error que nadie sospecha.
- **Solo el tramo que decide.** Para el desenlace se oyen los últimos 90 segundos, no la llamada
  entera (`src/disposition.py`, `--listening-sheet`). Una llamada auditada son dos minutos, no
  siete.
- **El oído manda y queda registrado.** En las celdas escuchadas, lo oído reemplaza al voto, y
  el rastro se publica sin contenido en `data/public/escucha_compromisos.json`.

Con 50 llamadas al mes a dos minutos cada una son **menos de dos horas de un analista**, contra
los 2.700 USD mensuales de cómputo que cuesta procesar 100.000 llamadas. El control humano no es
el cuello de botella: es la partida más pequeña del presupuesto.

## Lo que esto no resuelve

- **Deriva de población.** Si la cartera cambia —otro tramo de mora, otra ciudad, otro producto—,
  el acierto medido sobre la cartera vieja no se transfiere. La señal barata que lo delata es la
  tasa de desacuerdo de la capa 2; la cara es recalibrar.
- **Un sesgo compartido por los tres anotadores y por quien escucha.** La escucha la hace una
  persona con la misma rúbrica en la mano. Para un dato con consecuencia legal haría falta un
  segundo oyente independiente y medir el acuerdo entre humanos, no solo humano contra panel.
- **La transcripción.** Todas las capas miden sobre texto. Un error sistemático del transcriptor
  en un brazo y no en el otro las atraviesa enteras. Por eso se transcribe dos veces con modelos
  distintos y se anota sobre las dos, y por eso se descartaron las métricas que dependen de
  separar hablantes (`docs/decisiones.md` §1).

## La regla que se cumplió aunque costara

La segunda rúbrica —desenlace y reacción del interlocutor— tiene sus 300 anotaciones completas y
**no está en el informe**. La regla de publicación se escribió antes de anotar y exige un AC1 de
Gwet de al menos 0,6 en los dos brazos, que sale de la capa 4, y esa escucha no se hizo.

El dato que se quedó fuera es el más favorable al agente de IA de todo el trabajo: reconoce la
dificultad y ofrece una alternativa en 15 de 19 casos, frente a 9 de 22 de los humanos. Se
documenta en `docs/decisiones.md` §18 y no se publica.

Una regla de calidad que solo se aplica cuando el resultado no gusta no es una regla.

## Lo que el anclaje no puede ver

El anclaje de citas comprueba que cada afirmativa exista en la transcripción: 258 de 259. Esa
cifra es **precisión, y no tiene contraparte de recall**. El mecanismo solo puede verificar lo
que el panel marcó; por construcción no puede ver lo que el panel *no* marcó.

Y ahí está el modo de fallo que la literatura de extracción con evidencia reporta de forma
consistente: precisión alta y recall bajo, con modelos que «a menudo no extraen a menos que la
señal sea inequívoca». Traducido a este corpus: una promesa de pago implícita, dicha de forma
oblicua, es invisible para las cinco capas.

**No se ha verificado nunca una sola celda donde los tres anotadores dijeran que no.** La
escucha del §17 tocó las 14 celdas sin unanimidad, que son por definición las dudosas. El hueco
se cierra escuchando entre 30 y 50 negativos unánimes tomados al azar por variable clave, lo que
daría la tasa de verdaderos negativos que hoy no existe. No se hizo, y por eso se dice aquí.

## Cuánta independencia tiene el panel, medida

«Vale la mayoría de dos sobre tres» suena a tres opiniones. Dos de los tres anotadores comparten
familia de modelo, y la literatura de paneles de jueces documenta que los errores entre modelos
están correlacionados —más cuanto mejores son los modelos—, de modo que el voto puede valer
menos de lo que su número sugiere.

Medido sobre las 1.100 celdas de este corpus, y publicado en `data/public/agreement.json`:

| par | acuerdo global | acuerdo en las 58 celdas disputadas |
|---|---|---|
| Sonnet × Opus (auditor) | 1.051 / 1.100 | 9 / 58 |
| Sonnet × Opus (reauditor) | 1.048 / 1.100 | 6 / 58 |
| **Opus × Opus** | **1.082 / 1.100** | **40 / 58** |

El acuerdo global no dice nada: con una tasa base tan baja, los tres coinciden en los «no». Lo
que importa es la última columna. **Cuando el panel se parte, en 40 de 58 casos la mayoría la
forman los dos anotadores de la misma familia**, y el tercero queda fuera. Es decir: justo donde
la medición es frágil, el voto de tres se comporta como un voto de una familia.

Eso no invalida el consenso —la escucha de esas celdas lo corrigió donde hacía falta—, pero sí
acota lo que se puede afirmar sobre él, y por eso está en las limitaciones del informe.

La solución de libro es diversificar familias de modelos. Aquí no era ejecutable: el proyecto se
anota con agentes internos, sin llamadas a API externas, por la regla de que ningún audio ni
texto de las llamadas sale a un servicio de terceros. Medir y publicar la dependencia es lo que
se puede hacer, y es más honesto que no mirarla.

## Qué haría fallar un cambio

Una puerta necesita un umbral, y el umbral no puede ser un número redondo elegido a ojo. El
procedimiento defendible, con las 100 llamadas como conjunto congelado:

- **Diferencias pareadas sobre las mismas llamadas**, no dos muestras independientes. Los
  puntajes por ítem entre modelos están correlacionados, así que el pareado es lo que da
  potencia.
- **Errores estándar agrupados por llamada.** Los once campos de una misma llamada no son
  independientes; tratarlos como tales subestima el error, y en evaluaciones publicadas el
  error agrupado llega a ser el triple del ingenuo.
- **El umbral se pone en el ruido del propio instrumento, no más fino.** Aquí ese suelo está
  medido: el 5,3 % de celdas sin unanimidad. Una puerta que dispare por debajo de eso caza
  ruido y acaba desactivada, que es la forma habitual en que mueren estas puertas.

## El siguiente paso, nombrado

La capa 4 hoy estima **el acierto del panel**. Con un estrato tomado al azar y con probabilidad
de muestreo conocida, esas mismas escuchas pueden corregir **la cifra publicada**: es lo que
hacen los estimadores de inferencia asistida por predicción, que combinan una muestra pequeña
etiquetada por humanos con una masa grande etiquetada por el modelo y devuelven estimaciones
insesgadas con intervalos válidos, sin suponer nada sobre el modelo.

Importa porque usar etiquetas de un modelo directamente en un análisis posterior sesga el
estimador aunque el modelo acierte el 90 %: la cobertura de un intervalo del 95 % puede caer al
40 %. Con 100 llamadas eso no estrecharía los intervalos de este informe; los haría correctos.
Es el cambio que haría si esto pasara a producción, y se dice aquí en vez de fingir que ya está.

## Por rebanadas, no solo en global

Una tasa global esconde el subconjunto que importa. Las rebanadas de este corpus, todas
calculables desde `data/public/`, son: brazo; si la llamada retoma un acuerdo previo (26 de 50
humanas contra 0 de 50 de IA, la que más desbalancea); si hubo contacto con el titular; las
celdas sin unanimidad; las conductas con pocos positivos, que pueden irse a cero sin mover la
métrica global; y la duración de la transcripción, que es el modo de fallo clásico de una
extracción.

Con 20 a 30 casos por rebanada eso sirve para **ver dónde cayó algo**, no para decidir con
significancia. Decirlo evita el error de leer una rebanada pequeña como un hallazgo.
