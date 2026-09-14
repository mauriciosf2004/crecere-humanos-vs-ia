# Agentes humanos frente a agentes de IA en gestión de cobranza

Prueba técnica para Creceré AI. Cien llamadas —50 de gestores humanos y 50 de un agente de IA—
convertidas en datos para responder una pregunta: ¿hay diferencias sustentables en cómo gestionan?

**Respuesta corta.** Sí, pero dicen cómo cobra cada canal, no cuál cobra mejor. La IA se presenta
como área jurídica y afirma que la oferta vence hoy; en las llamadas humanas se prometen
beneficios sobre el historial crediticio. Qué canal consigue más compromisos de pago no se puede
saber con estas grabaciones: los humanos retomaban sobre todo acuerdos ya pactados y la IA abría
gestiones nuevas. El siguiente paso es un piloto con asignación de cuentas al azar.

## Las cuatro preguntas del encargo

| Pregunta | Respuesta corta | Dónde está |
|---|---|---|
| Desempeño: ¿quién es más efectivo? | En compromisos de pago no hay ganador demostrable | informe, hallazgo 5 |
| Explicación: ¿qué explica las diferencias? | El guion (encuadre jurídico, vencimiento, amenaza) y la cartera (acuerdos previos) | `docs/decisiones.md` §10 y §13 |
| Conducta: ¿qué hace mejor cada uno? | Con criterio de cumplimiento, la IA casi no promete beneficios crediticios; los humanos no se presentan como área jurídica ni presionan con el vencimiento | informe, veredicto |
| Mejora: ¿qué cambiar? | Un piloto con asignación al azar y una variante de la IA sin amenaza ni vencimiento | informe, siguiente paso |

## Por dónde empezar

1. `report/index.html` — el informe, dos páginas.
2. `docs/hipotesis.md` — qué se quería entender, qué se podía medir, qué se esperaba y qué cambió respecto al primer registro.
3. `docs/decisiones.md` — las decisiones que cambiaron el resultado, cada una con el dato que la sostiene.
4. `src/analyze.py` — el contraste estadístico.

`docs/variables-descartadas.md` lista las 39 candidatas que no entraron en la familia y por qué.

## Cómo está hecho

| Paso | Comando | Qué hace | Necesita |
|---|---|---|---|
| Inventario | `make inventory` | formato y duración de cada audio | audios |
| Transcripción | `make transcribe` y `uv run python -m src.transcribe --model large-v3` | dos pasadas locales con whisper.cpp | audios, `whisper-cli`, modelos ggml en `~/.whisper-models/` |
| Panel | `uv run python -m src.annotate --stage` → `workflows/panel-anotacion.js` (tool Workflow de Claude Code) → `uv run python -m src.annotate --from-workflow <salida>` | tres agentes ciegos anotan cada llamada, se vota por mayoría y se aplica la regla literal de fecha | transcripciones, extracciones (`make extract`), Claude Code |
| Contraste | `make analyze` | test global y Westfall-Young sobre el consenso, en el total y dentro de las gestiones nuevas | consenso del panel |
| Anclaje | `make anchoring` | comprueba que cada cita existe en las transcripciones | consenso del panel |
| Informe | `make report` | arma `results.json` y renderiza el HTML | `data/public/` |
| Puerta | `make verify` | falla si el informe no ocupa exactamente dos páginas; probado en macOS (`CHROME=<ruta>` en otro sistema) | Chrome, `pdfinfo` |

`make extract` es la pasada única original, de un solo modelo. Se conserva para compararla con el
panel (`docs/decisiones.md`, §13) y como fuente de citas de la regla literal de fecha (§14): una cita
suya solo cuenta si existe en la transcripción. Los audios los entrega Creceré y no se versionan.

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
