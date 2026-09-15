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
