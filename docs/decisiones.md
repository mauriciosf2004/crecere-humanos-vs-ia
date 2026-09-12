# Registro de decisiones

Las decisiones que cambiaron el resultado, con el motivo y —donde lo hubo— el dato que las
sostiene. Está en el repositorio porque una decisión sin su razón no se puede auditar, y varias
de estas se tomaron *contra* la opción más vistosa.

---

## 1. No diarizar. Y por tanto, no medir reparto del habla, latencia ni interrupciones

El audio es mono de 8 kHz. Separar agente de deudor exigía diarización acústica, que era
además la vía a las métricas conversacionales más atractivas del encargo.

Se sondeó antes de adoptarla y el error resultó **diferencial por brazo**: sobre una muestra,
el clúster dominante acaparaba más del 90 % del habla en 3 de 8 llamadas humanas y en 0 de 8 de
IA. La voz sintética es homogénea, de nivel constante y sin ruido de fondo, así que el embedding
la separa mejor. Eso no es una virtud del producto: es una ventaja estructural del brazo de IA
**en la medición**.

Publicar "la IA reparte mejor la conversación" sobre esa base habría sido reportar un artefacto
como hallazgo, y encima a favor del cliente que evalúa el trabajo. Se descartaron las tres
métricas que dependen de la frontera del turno.

**Consecuencia de diseño:** todas las variables que quedaron se definen por la **presencia** de
una frase concreta del agente. Ninguna por ausencia. Es lo que las hace inmunes tanto al error
de diarización como a las alucinaciones del transcriptor.

## 2. Separar el nombre del área de la amenaza al deudor

Un primer barrido léxico daba una diferencia enorme en "presión jurídica". Al leer qué estaba
contando, casi todos los positivos de la IA eran la misma frase de presentación: *"del área de
embargos, judicializaciones y alivios financieros"*. Es el nombre del departamento, no una
amenaza.

El constructo estaba mal. Se partió en dos variables con frontera de contenido —quién soy,
frente a qué pasa si no paga— y ambas se miden por separado. El efecto de la segunda baja de
+48 a +38 puntos al hacerlo bien.

**La lección se aplicó a toda la rúbrica:** cada variable lleva documentado qué la haría dar un
falso positivo.

## 3. Corregir el regex: "sin embargo" contiene "embargo"

El mismo barrido contaba como presión jurídica cualquier llamada con la palabra "embargo",
incluida la conjunción. Eran **7 falsos positivos en el brazo humano y 0 en el de IA**.

Inflaban el conteo humano, así que el sesgo iba en dirección conservadora: corregido, la
diferencia sube de +52 a +56 puntos. Es el tipo de error que no cambia el signo pero sí el
número, y el número es lo que se publica.

## 4. Limpiar las alucinaciones del transcriptor antes de anotar

Whisper inventa texto en los silencios largos, casi siempre fórmulas de YouTube ("suscríbete al
canal", "gracias por ver el video"). Aparecen en **14 de 50 llamadas humanas y en 1 de 50 de
IA** (Fisher p = 0,0004): las llamadas humanas tienen más silencio.

Pesan el 0,29 % de las palabras y ninguna variable de la familia puede dispararse por ellas
—las ocho se definen por presencia de una frase del agente—, pero se eliminan igual antes de
que el modelo las lea. La asimetría se declara en el método: es una propiedad del instrumento,
no de los agentes.

## 5. Descartar el contraste de equivalencia (TOST)

Dos de las ocho hipótesis predicen que no habrá diferencia, y con poca potencia un p-valor alto
no permite afirmar nada. El contraste de equivalencia sería la herramienta correcta.

Se simuló antes de adoptarlo: con 50 por brazo, la probabilidad de poder **declarar**
equivalencia es del **0,3 % con un margen de ±10 puntos** y del **0 % con ±5**. Es inalcanzable.

Montar el aparato para no poder concluir nunca es peor que no montarlo. Se reporta el intervalo
de confianza, que comunica lo mismo sin fingir rigor.

## 6. Westfall-Young, y por qué no Bonferroni

Se simuló la ganancia antes de elegir. Con desenlaces independientes, Westfall-Young es
idéntico a Holm. Con correlación de 0,7 —el escenario real, porque varias variables miden
partes del mismo guion— gana unos **5 puntos de potencia**.

Se adoptó sabiendo cuánto compra. Bonferroni sobre esta familia habría hundido la potencia
individual sin comprar ninguna garantía adicional.

## 7. Un test global como compuerta, en vez de una métrica primaria única

La alternativa ortodoxa era declarar una métrica primaria antes de ver los datos y dejar el
resto como exploratorio. Se descartó por una razón práctica: obliga a apostar por una variable
cuando lo que se quería era explorar la familia entera.

El test global no exige saber qué variable importa —pregunta si los perfiles difieren— y al
actuar de compuerta mantiene el error por familia en el 5 %. La arquitectura replica el orden
de la pregunta del encargo: primero si existen diferencias, después cuáles.

Se verificó por simulación que ninguno de los dos enfoques domina: el test global gana cuando
la diferencia está repartida entre muchas variables (29 % frente a 20 % de potencia en un
escenario de ocho efectos pequeños) y pierde cuando está concentrada en una sola (63 % frente
a 92 %). Se eligió con ese mapa delante.

## 8. Ocho variables, ni más ni menos

Veintiocho candidatas, ocho supervivientes. Los motivos de descarte, por frecuencia:

- **Artefacto de medición.** Dependían de la prosodia, de la segmentación del transcriptor o de
  la calidad de la voz sintética. Ejemplo: la adherencia a guion medida por n-gramas repetidos.
- **Constructo ambiguo.** El signo cambiaba según dónde se pusiera la frontera. Ejemplo: la
  pregunta por el motivo del impago, que se invierte según se exija que el motivo sea pasado.
- **Denominador condicional.** Definidas solo en un puñado de llamadas, con potencia por debajo
  de 0,05. Ejemplo: la revelación de la deuda a un tercero, definida en 6-7 llamadas por brazo.
- **Redundancia.** Medían lo mismo que otra ya incluida. Dos variables con efectos de +52 y +56
  puntos se descartaron por esto, pese a su tamaño: eran nodos del mismo bloque del guion y
  habrían diluido el test global sin añadir información.
- **Base insuficiente.** Un solo caso en 100 llamadas. Es el caso de que el deudor verbalice que
  cree hablar con una máquina: la mejor cita del corpus y la peor variable posible.

El detalle de las veinte descartadas está en el historial del diseño de la rúbrica.

## 9. Pasar el texto por stdin y no como argumento

Una llamada fallaba siempre y la causa no era el modelo: su transcripción empieza por `-Aló.` y
el texto se pasaba como argumento posicional, así que el CLI leía el guion inicial como una
opción desconocida y salía sin escribir nada.

Era el único caso del corpus, pero habría reaparecido con cualquier transcripción que empiece
por guion. Se corrigió pasando el texto por la entrada estándar.
