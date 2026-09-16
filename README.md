# Agentes humanos frente a agentes de IA en gestión de cobranza

[![ci](https://github.com/mauriciosf2004/crecere-humanos-vs-ia/actions/workflows/ci.yml/badge.svg)](https://github.com/mauriciosf2004/crecere-humanos-vs-ia/actions/workflows/ci.yml)

Prueba técnica para Creceré AI. Cien llamadas —50 de gestores humanos y 50 de un agente de IA—
convertidas en datos para responder una pregunta: ¿hay diferencias sustentables en cómo gestionan?

**Respuesta corta.** Sí, pero dicen cómo cobra cada canal, no cuál cobra mejor. La IA se presenta
como área jurídica y afirma que la oferta vence hoy; en las llamadas humanas se prometen
beneficios sobre el historial crediticio. Qué canal consigue más compromisos de pago no se puede
saber con estas grabaciones: los humanos retomaban sobre todo acuerdos ya pactados y la IA abría
gestiones nuevas. El siguiente paso es un piloto con asignación de cuentas al azar.

Con cifras: se presenta como área jurídica en 43 de 50 llamadas de IA y 1 de 50 humanas; promete
beneficio crediticio en 3 de 50 frente a 22 de 50; y el compromiso con fecha y monto va 9 de 31
contactos con titular frente a 17 de 46, una diferencia que esta muestra no resuelve (el intervalo
va de 32 puntos porcentuales abajo a 1 arriba).

Desde un clon limpio, `make report` regenera `report/index.html` y `git status` queda vacío:
ningún número del informe está escrito a mano.

## Las cuatro preguntas del encargo

| Pregunta | Respuesta corta | Dónde está |
|---|---|---|
| Desempeño: ¿quién es más efectivo? | En compromisos de pago no hay ganador demostrable | informe, hallazgo 5 |
| Explicación: ¿qué explica las diferencias? | El guion (encuadre jurídico, vencimiento, anuncio de proceso legal) y la cartera (acuerdos previos) | `docs/decisiones.md` §10 y §13 |
| Conducta: ¿qué hace mejor cada uno? | La IA se presenta como área jurídica y dice que la oferta vence hoy; los humanos prometen más beneficios crediticios | informe, veredicto |
| Mejora: ¿qué cambiar? | Un piloto con asignación al azar, una variante de la IA sin anuncio legal ni vencimiento y un estándar común para los dos canales | informe, siguiente paso |

## Por dónde empezar

1. **[El informe](https://mauriciosf2004.github.io/crecere-humanos-vs-ia/report/)** — dos páginas, pensado para imprimirse. El archivo es `report/index.html`.
2. `docs/hipotesis.md` — qué se quería entender, qué se esperaba, la tabla completa de las ocho hipótesis con su resultado, y el pre-registro del desenlace (§7).
3. `docs/decisiones.md` — las decisiones que cambiaron el resultado, cada una con el dato que la sostiene.
4. `docs/panel-de-anotacion.md` — cómo anotan los tres agentes ciegos y por qué se vota 2 de 3.
5. `docs/control-de-calidad.md` — qué cuesta saber que esto sigue acertando con cien mil llamadas.
6. `src/analyze.py` — el contraste estadístico.

`docs/variables-descartadas.md` lista las 39 candidatas que no entraron en la familia y por qué.

## Anotar con agentes, especificado

Las cien llamadas no las etiquetó una persona ni una sola pasada de un modelo: las anotan **tres
agentes ciegos** que no se ven entre sí, y cada celda se queda con la respuesta de al menos dos.
El trabajo está especificado, no improvisado, y esa especificación es parte del repositorio:

| Pieza | Qué gobierna |
|---|---|
| `CLAUDE.md` | El contrato del proyecto: qué se versiona y qué no, la regla de PII, la prohibición de escribir una cifra a mano, y la definición de «hecho» |
| `src/rubric.md`, `src/rubric_desenlace.md` | Las dos rúbricas, congeladas antes de anotar; su huella entra en la caché, así que editarlas invalida las anotaciones |
| `src/schema.json`, `src/schema_desenlace.json` | La salida válida: conjuntos cerrados, sin texto libre |
| `workflows/panel-anotacion.js` | La orquestación: tres roles, dos modelos, reanudable por lotes |
| `docs/hipotesis.md` | El pre-registro: hipótesis, cortes y regla de publicación, con fecha y commit |

La disciplina que lo hace verificable es la misma en todas partes: **cada respuesta afirmativa
obliga a citar una frase literal, y el código comprueba que esa frase exista en la
transcripción**. 258 de 259 quedaron ancladas. Una etiqueta que no se puede anclar no entra.

`src/results.py` cierra el círculo por el otro lado: la prosa del informe declara los supuestos
de los que depende, y si el análisis deja de sostener una frase, el armado falla en vez de
publicarla.

## Sobre el diseño

El informe usa la identidad de Creceré AI —su magenta y Poppins— con una regla que lo gobierna
todo: **el rosa es identidad, no información**. El rosa de marca tiene 2,67:1 de contraste sobre
blanco, así que no pasa ni el umbral para elementos gráficos: va como filete de firma y nada más.
Donde la familia rosa tiene que leerse se usa `#7a2c68`, que da 8,80:1.

Los colores de los datos no son de marca sino de legibilidad: el informe se fotocopia y las dos
series se separan 21,8 de ΔL* en escala de grises. El magenta secundario de la marca queda a 2,5
del ocre, indistinguible impreso, así que no entra.

Poppins va **embebida en base64** dentro del HTML (24 KB, subconjunto latino, licencia SIL OFL;
ver `report/fonts/LICENSE.txt`) y solo en títulos y rótulos. Embebida, el informe se compone
igual en cualquier máquina: sin eso, un Linux sin las caras del sistema cae en una más ancha y se
va a tres páginas, que es justo lo que CI detectó.

## Cómo está hecho

| Paso | Comando | Qué hace | Necesita |
|---|---|---|---|
| Inventario | `make inventory` | formato y duración de cada audio | audios |
| Transcripción | `make transcribe` y `uv run python -m src.transcribe --model large-v3` | dos pasadas locales con whisper.cpp | audios, `whisper-cli`, modelos ggml en `~/.whisper-models/` |
| Panel | `uv run python -m src.annotate --stage` → `workflows/panel-anotacion.js` (tool Workflow de Claude Code) → `uv run python -m src.annotate --from-workflow <salida>` | tres agentes ciegos anotan cada llamada, se vota por mayoría y se aplica la regla literal de fecha | transcripciones, extracciones (`make extract`), Claude Code |
| Contraste | `make analyze` | test global y Westfall-Young sobre el consenso, en el total y dentro de las gestiones nuevas | consenso del panel |
| Anclaje | `make anchoring` | comprueba que cada cita existe en las transcripciones | consenso del panel |
| Desenlace | panel con `src/rubric_desenlace.md` → `make disposition` | cómo termina la llamada (incluido el acuerdo parcial) y cómo responde el interlocutor; exploratorio, pre-registrado en `docs/hipotesis.md` §7 y con su resultado en `docs/decisiones.md` §18 | transcripciones, Claude Code |
| Informe | `make report` | arma `results.json` y renderiza el HTML | `data/public/` |
| Puerta | `make verify` | falla si el informe no ocupa exactamente dos páginas; probado en macOS (`CHROME=<ruta>` en otro sistema) | Chrome, `pdfinfo` |

Los audios los entrega Creceré y no se versionan.

`make check` pasa formato, linting y tests. `make help` lista todo.

## Qué hay en el repositorio y qué no

Las llamadas son de deudores reales. Los audios, las transcripciones y las anotaciones del modelo
(`data/raw`, `data/interim`, `data/processed`) **no se versionan**. Lo que sí está es
`data/public/`: variables derivadas y conteos, sin una palabra del texto de ninguna llamada. La
tabla analítica completa, una fila por llamada, es `data/public/features.csv`.

Desde un clon limpio funcionan `make report`, `make verify` y `make check`. Transcribir y extraer
requiere los audios originales.

## Requisitos

Python 3.11 o superior con [uv](https://docs.astral.sh/uv/). Para el pipeline completo, además:
`ffmpeg`, `whisper-cli` (paquete `whisper-cpp` de Homebrew), el CLI de Claude Code, Google Chrome
y `pdfinfo` (poppler).
