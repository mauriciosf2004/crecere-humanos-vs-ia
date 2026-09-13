# Registro de decisiones

Las decisiones que cambiaron el resultado, con el motivo y —donde lo hubo— el dato que las
sostiene. Está en el repositorio porque una decisión sin su razón no se puede auditar, y varias
de estas se tomaron *contra* la opción más vistosa.


## Cómo cambió la conclusión sobre los compromisos de pago

La conclusión comercial cambió tres veces. Los mensajes de esos commits reflejan lo que se sabía en
cada momento; esta tabla es la lectura vigente.

| Commit | Qué cambió en la medición | Compromisos IA / humano | Diferencia | Lectura |
|---|---|---|---|---|
| `cb0e273` | Extracción de un modelo, con el ordinal mal leído | 15 / 38 | −46 pp, significativa | Brecha a favor del humano |
| `f6644f4` | Solo cuenta el nivel calificado | 11 / 25 | −28 pp, p aj. 0,014 | Brecha a favor del humano |
| `74490c5` | Estratificación por acuerdo previo | 11 / 25 | p estratificado 0,13 | No atribuible al agente |
| `d60b561` | Consenso del panel de tres anotadores | 9 / 17 | −16 pp, p aj. 0,196 | No se detecta diferencia |
| §14 | Rúbrica literal para «hoy» en la propuesta con cifras | 9 / 17 | −16 pp, p aj. 0,295 | No se detecta diferencia |


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

Se adoptó sabiendo cuánto compra.

Se verificó además sobre la correlación real del corpus, reconstruida por cópula gaussiana:
en 600 réplicas bajo nulo completo, el error por familia de Westfall-Young es 0,042 [IC95
0,028–0,061] y el del procedimiento con compuerta, 0,025 [0,015–0,041]. Bonferroni sobre esta familia habría hundido la potencia
individual sin comprar ninguna garantía adicional.

## 7. Un test global como compuerta, en vez de una métrica primaria única

La alternativa ortodoxa era declarar una métrica primaria antes de ver los datos y dejar el
resto como exploratorio. Se descartó por una razón práctica: obliga a apostar por una variable
cuando lo que se quería era explorar la familia entera.

El test global no exige saber qué variable importa —pregunta si los perfiles difieren—.
El error por familia no lo controla la compuerta sino Westfall-Young, que lo mantiene en el 5 %
por sí solo. La arquitectura replica el orden
de la pregunta del encargo: primero si existen diferencias, después cuáles.

Se verificó por simulación que ninguno de los dos enfoques domina: el test global gana cuando
la diferencia está repartida entre muchas variables (29 % frente a 20 % de potencia en un
escenario de ocho efectos pequeños) y pierde cuando está concentrada en una sola (63 % frente
a 92 %). Se eligió con ese mapa delante.

La rúbrica y el esquema rotulan todavía el compromiso de pago como «métrica primaria». Son el
instrumento tal como se ejecutó y no se editan a posteriori: la huella de la rúbrica forma parte
de la caché de extracción, y cambiarla invalidaría las cien anotaciones. El rótulo es anterior a
esta decisión.

## 8. Ocho variables, ni más ni menos

Cuarenta y siete candidatas, ocho en la familia. Los motivos de descarte, por frecuencia:

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

La lista completa, agrupada por motivo, está en `docs/variables-descartadas.md`.

## 9. Pasar el texto por stdin y no como argumento

Una llamada fallaba siempre y la causa no era el modelo: su transcripción empieza por `-Aló.` y
el texto se pasaba como argumento posicional, así que el CLI leía el guion inicial como una
opción desconocida y salía sin escribir nada.

Era el único caso del corpus, pero habría reaparecido con cualquier transcripción que empiece
por guion. Se corrigió pasando el texto por la entrada estándar.

## 10. Los dos brazos no atacaron la misma cartera

> Cifras de la extracción original, de un solo modelo. Con el panel de tres anotadores la
> composición se vuelve más nítida y cambia la lectura del compromiso de pago: ver el §13.

Sin metadatos no había forma de comprobar el balance entre brazos, así que se midió desde el
audio. La señal más limpia es si la llamada **retoma un acuerdo de pago ya existente**: se detecta
por una frase concreta del agente —una frase que retoma el monto y las cuotas ya pactadas— y no por
ausencia.

| | IA | Humano |
|---|---|---|
| Retoma un acuerdo previo | 4/50 | 32/50 |

Los humanos estaban, en su mayoría, dando seguimiento a acuerdos; la IA, abriendo gestiones
nuevas. Se comprobó que es la cartera y no el guion: en ninguna de las 46 llamadas de IA sin
acuerdo previo aparece una referencia a uno anterior, ni en boca del agente ni del deudor.

Al estratificar por esa variable (Mantel-Haenszel, dos estratos):

- Las cuatro diferencias de encuadre y de promesa **se mantienen** (p < 0,001 en las cuatro).
- La verificación de identidad **se debilita** (p = 0,08).
- La diferencia en **compromisos de pago no se puede separar de la composición** (p = 0,13). En
  el único estrato con llamadas suficientes de ambos brazos —gestiones nuevas— la brecha baja a
  17 puntos (IA 10/46, humano 7/18). El estrato de acuerdo previo tiene 4 llamadas de IA: no hay
  con qué comparar.

Por eso la brecha comercial se presenta como observada pero **no atribuible al tipo de agente**,
y la conclusión que se sostiene es la de conducta.

No se estratificó por "habla con el titular" (IA 22/50, humano 44/50): en 19 llamadas de IA el
interlocutor no se puede determinar, frente a 3 humanas, y esa indeterminación se define por
ausencia de confirmación, que es justo el tipo de variable que se descartó en el §1.

## 11. Validar sin escuchar: el anclaje de citas

> Cifras de la extracción original. Con el panel, 258 de 260 afirmativas anclan: ver los §13 y §14.

Escuchar las llamadas contra lo anotado es el siguiente paso de la validación. Antes de eso se puede
comprobar una parte por máquina: la rúbrica obliga a citar literalmente la frase que justifica cada
respuesta afirmativa, así que basta con buscar esa frase en la transcripción que leyó el modelo.

De 273 respuestas afirmativas, **262 citan una frase que aparece
literalmente** (96 %). De las 11 restantes, 10 están en las variables
comerciales —compromiso de pago, propuesta con cifras y cuotas— y la otra en la caducidad de la oferta. Las tres diferencias
de encuadre y de promesa —presentación jurídica, amenaza legal y promesa crediticia— están
ancladas al 100 %.

Las dos variables de contexto —si la llamada retoma un acuerdo previo y quién contesta— se
anclan igual, porque el argumento de que los dos brazos no son comparables descansa entero
sobre ellas: 101 de 102 citas aparecen literalmente.

Anclada no significa bien interpretada, pero descarta la invención, que es el fallo que más daño
haría. Y dice dónde escuchar: las citas no ancladas y los positivos de las celdas raras —los que
sostienen la dirección de un efecto— forman la hoja de escucha, que vive en `data/interim/` porque
contiene texto de las llamadas.

## 12. Una segunda transcripción, con otro modelo

La primera transcripción usó whisper large-v3-turbo. Para no depender de un solo transcriptor, las
100 llamadas se volvieron a transcribir con large-v3 completo, en local y con la misma
configuración, y los anotadores del panel reciben las dos versiones.

Comparando las dos palabra a palabra, tras la misma limpieza:

| | Humano | IA |
|---|---|---|
| Coincidencia mediana entre transcriptores | 0,886 | 0,924 |
| Llamadas con fórmulas alucinadas (turbo) | 14 de 50 | 1 de 50 |
| Llamadas con fórmulas alucinadas (large-v3) | 4 de 50 | 0 de 50 |

Tres consecuencias. La primera: **el error de transcripción también es diferencial por brazo** —las
dos versiones coinciden menos en las llamadas humanas (Mann-Whitney p = 0,0003)—, como ya lo era el
de la separación de hablantes.

La segunda: large-v3 inventa mucho menos texto en los silencios, que es donde la voz humana deja más
huecos.

La tercera, y la que decide el diseño: **ninguno de los dos transcriptores domina.** Los cortes
graves —una versión con menos de la mitad de palabras que la otra— son pocos, uno en cada sentido y
los dos en llamadas humanas: large-v3 dejó 5 palabras donde turbo tenía 196, y turbo 27 donde
large-v3 tenía 60. Dos casos no hacen un patrón, pero bastan para ver que cada transcriptor pierde
trozos que el otro conserva, y que elegir uno habría sido elegir qué errores aceptar. Por eso los
anotadores reciben las dos lecturas.

## 13. Tres anotadores en lugar de uno

La extracción original fue una sola pasada de un solo modelo. Para no depender de ella, las 100
llamadas las anotaron tres agentes internos por separado —un clasificador con Sonnet, un auditor y un
reauditor con Opus—, sin ver lo que respondieron los otros ni saber de qué brazo era cada llamada, y
cada celda se quedó con la respuesta de al menos dos de tres. Las instrucciones literales están en
`docs/panel-de-anotacion.md`.

- De 1.100 celdas, **1.042 salieron unánimes**, 55 con dos votos de tres y 3 sin mayoría.
- La ceguera se verificó en los registros de los 300 agentes: ninguno abrió nada fuera de la rúbrica
  y la carpeta de su llamada.
- 249 de 250 respuestas afirmativas citan una frase que existe en las transcripciones, frente a 262
  de 273 en la pasada única (258 de 260 tras la regla del §14).

**La pasada única tenía un sesgo, y en una sola dirección.** Donde más cambió fue el compromiso de
pago: el panel bajó de calificado a vago 8 compromisos humanos y 2 de IA, y no subió ninguno a
calificado. En los casos unánimes, los tres anotadores ven la misma fecha y el mismo monto que vio la
extracción; lo que no aceptan como aceptación es un asentimiento vago —un «ya veré» o un simple «de acuerdo»— ni un número de cuota como monto.

| | Extracción (un modelo) | Panel (tres) |
|---|---|---|
| Compromisos calificados, IA / humano | 11 / 25 | 9 / 17 |
| Retoma un acuerdo previo, IA / humano | 4 / 32 | 0 / 26 |
| Propuesta con cifras, IA / humano | 28 / 29 | 19 / 29 |

**Qué cambia en las conclusiones.** Las diferencias de encuadre y de promesa no se mueven:
presentación jurídica 43 frente a 1, oferta que vence hoy 27 frente a 1, amenaza legal 21 frente a
2, promesa crediticia 3 frente a 22. La verificación de identidad (14 frente a 1) parecía sostenerse
también dentro del mismo tipo de gestión; el §14 corrige esa lectura. En cambio, **la diferencia en compromisos de pago deja de
ser significativa incluso antes de estratificar**: 9 frente a 17, −16 puntos, IC95 [−32, +1]. Con la
extracción original parecía una brecha que la cartera explicaba; con el panel ni siquiera se detecta.

La composición de las carteras, en cambio, se vuelve más nítida: con el panel ninguna llamada de IA
retoma un acuerdo previo, frente a 26 humanas. La comparación estratificada es, en la práctica, la
de las gestiones nuevas.

## 14. Leer la rúbrica al pie de la letra, y corregir también dentro de las gestiones nuevas

**«Hoy» es una fecha.** La rúbrica, congelada antes de anotar, cuenta `hoy` como fecha resoluble en la
propuesta con cifras. En 10 llamadas de IA la única fecha era el vencimiento de la oferta —«vencería
hoy mismo»— y el panel no la aceptó. La extracción original sí. Había dos caminos: volver a anotar
con otra instrucción o aplicar la regla ya escrita. Se eligió la regla escrita, porque cambiar la
interpretación después de ver el resultado es justo el camino que abre falsos hallazgos.

La regla se aplica en código, después del voto (`apply_literal_date_rule` en `src/annotate.py`): si la
celda no quedó afirmativa y alguna anotación de esa llamada —del panel o de la extracción— la marcó
afirmativa con una cita que tiene un monto y «hoy», la celda pasa a afirmativa con esa cita. Es
simétrica entre brazos; cambió 10 llamadas de IA y ninguna humana, y las 10 citas anclan.

| Propuesta con cifras | Antes | Después |
|---|---|---|
| IA / humano | 19 / 29 | 29 / 29 |
| Diferencia | −20 pp, IC95 [−38, −1] | 0 pp, IC95 [−19, +19] |
| p ajustado | 0,125 | 1,000 |

La hipótesis H7 («sin diferencia») pasa a coincidir. El p ajustado del compromiso de pago sube de
0,196 a 0,295: en Westfall-Young el ajuste de cada variable depende de las demás, y la propuesta con
cifras dejó de ir por delante de él.

**La estratificación también se corrige por las ocho.** El p de Mantel-Haenszel de la verificación
de identidad (0,039) no estaba ajustado. Con Westfall-Young dentro de las gestiones nuevas —el único
estrato con los dos brazos— da 0,165, así que se rotula como no concluyente. Las otras cuatro
diferencias siguen por debajo de 0,01 también ahí.

