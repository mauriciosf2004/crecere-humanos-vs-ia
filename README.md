# Agentes humanos frente a agentes de IA en gestión de cobranza

Prueba técnica para Creceré AI. Cien llamadas —50 de gestores humanos y 50 de un agente de IA—
convertidas en datos para responder una pregunta: ¿hay diferencias sustentables en cómo gestionan?

**Respuesta corta.** Sí, pero dicen cómo cobra cada canal, no cuál cobra mejor. La IA se presenta
como área jurídica y afirma que la oferta vence hoy; en las llamadas humanas se prometen
beneficios sobre el historial crediticio. Qué canal consigue más compromisos de pago no se puede
saber con estas grabaciones: los humanos retomaban sobre todo acuerdos ya pactados y la IA abría
gestiones nuevas. El siguiente paso es un piloto con asignación de cuentas al azar.

## Por dónde empezar

1. `report/index.html` — el informe, dos páginas.
2. `docs/hipotesis.md` — qué se quería entender, qué se podía medir y qué se esperaba, antes de medir.
3. `docs/decisiones.md` — las decisiones que cambiaron el resultado, cada una con el dato que la sostiene.
4. `src/analyze.py` — el contraste estadístico.

`docs/variables-descartadas.md` lista las 39 candidatas que no entraron en la familia y por qué.

## Cómo está hecho

| Paso | Comando | Qué hace | Necesita |
|---|---|---|---|
| Inventario | `make inventory` | formato y duración de cada audio | audios |
| Transcripción | `make transcribe` | whisper.cpp en local, unos 18 min | audios, `whisper-cli`, modelo `ggml-large-v3-turbo` |
| Extracción | `make extract` | ocho preguntas cerradas con cita obligatoria, unos 4 USD | transcripciones, CLI de Claude Code |
| Contraste | `make analyze` | test global, Westfall-Young y estratificación por tipo de gestión | extracciones |
| Anclaje | `make anchoring` | comprueba que cada cita existe en la transcripción | extracciones |
| Informe | `make report` | arma `results.json` y renderiza el HTML | `data/public/` |
| Puerta | `make verify` | falla si el informe no ocupa exactamente dos páginas | Chrome, `pdfinfo` |

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
