# Pipeline del análisis. Cada paso escribe su salida en data/ y es re-ejecutable.
#
#   inventory → transcribe → panel → annotate → analyze → anchoring → report → verify
#
# El panel son tres agentes de Claude Code orquestados con workflows/panel-anotacion.js
# (docs/panel-de-anotacion.md). extract es la pasada única histórica; annotate aún toma de
# ella citas para la regla literal de fecha. Los audios, transcripciones y anotaciones no se
# versionan: desde un clon limpio corren `make report`, `make verify` y `make check`.
#
# pyenv exporta VIRTUAL_ENV y confunde a uv; lo quitamos del entorno.
unexport VIRTUAL_ENV
PY := uv run --quiet
CHROME ?= /Applications/Google Chrome.app/Contents/MacOS/Google Chrome

# report y verify DEBEN ser .PHONY: existe un directorio report/ y sin esto make responde
# "up to date" sin ejecutar nada, y la puerta de dos páginas deja de proteger.
.PHONY: help inventory transcribe extract annotate analyze anchoring disposition report verify test lint check clean

help: ## Muestra esta ayuda
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-11s %s\n", $$1, $$2}'

inventory: ## Inventario técnico del corpus: formato, duración, n analizable
	$(PY) python -m src.inventory

transcribe: ## Transcribe en local con whisper.cpp (requiere data/raw)
	$(PY) python -m src.transcribe

extract: ## Pasada única histórica: la rúbrica con el CLI de Claude Code (cacheada)
	$(PY) python -m src.extract

annotate: ## Vota las anotaciones del panel y aplica la regla literal de fecha
	$(PY) python -m src.annotate

analyze: ## Contrasta la familia sobre el consenso del panel y escribe data/public/effects.json
	$(PY) python -m src.analyze --source consenso

anchoring: ## Comprueba que cada positivo del consenso cita una frase de las transcripciones
	$(PY) python -m src.anchoring --source consenso

disposition: ## Consenso, anclaje y cortes del desenlace y la reacción del interlocutor (exploratorio)
	$(PY) python -m src.disposition

report: ## Arma results.json y renderiza report/index.html desde data/public/
	$(PY) python -m src.results
	$(PY) python -m src.report

verify: report ## Puerta dura: el informe debe ocupar exactamente 2 páginas
	@"$(CHROME)" --headless --disable-gpu \
		--no-pdf-header-footer --print-to-pdf=/tmp/crecere-report.pdf \
		"file://$(CURDIR)/report/index.html" 2>/dev/null \
		|| { echo "FALLO: no se pudo imprimir con Chrome. Fuera de macOS: make verify CHROME=<ruta>"; exit 1; }
	@n=$$(pdfinfo /tmp/crecere-report.pdf | awk '/^Pages:/{print $$2}'); \
	if [ "$$n" != "2" ]; then \
		echo "FALLO: el informe ocupa $$n páginas, deben ser exactamente 2."; exit 1; \
	else echo "OK: 2 páginas exactas."; fi

test: ## Tests: estadística, contraste, voto del panel, anclaje e informe
	$(PY) pytest tests/ -q

lint: ## Comprueba formato y linting, sin reescribir nada
	$(PY) ruff format --check src tests
	$(PY) ruff check src tests

check: lint test ## Todo lo que debe pasar antes de un commit

# clean nunca toca data/: las transcripciones y extracciones no se versionan, costaron
# 18 minutos de GPU y 4 USD, y un clean reflejo las destruiría sin vuelta atrás.
clean: ## Borra cachés de herramientas y el HTML generado
	rm -rf .pytest_cache .ruff_cache report/index.html
