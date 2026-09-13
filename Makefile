# Pipeline del análisis. Cada paso escribe su salida en data/ y es re-ejecutable.
#
#   inventory → transcribe → extract → annotate → analyze → report → verify
#
# transcribe y extract necesitan los audios originales (data/raw, no versionados), el
# binario whisper-cli y el CLI de Claude Code. Desde un clon limpio corren `make report`,
# `make verify` y `make check`, que parten de lo versionado en data/public/.
#
# pyenv exporta VIRTUAL_ENV y confunde a uv; lo quitamos del entorno.
unexport VIRTUAL_ENV
PY := uv run --quiet

# report y verify DEBEN ser .PHONY: existe un directorio report/ y sin esto make responde
# "up to date" sin ejecutar nada, y la puerta de dos páginas deja de proteger.
.PHONY: help inventory transcribe extract annotate analyze anchoring report verify test lint check clean

help: ## Muestra esta ayuda
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-11s %s\n", $$1, $$2}'

inventory: ## Inventario técnico del corpus: formato, duración, n analizable
	$(PY) python -m src.inventory

transcribe: ## Transcribe en local con whisper.cpp (requiere data/raw)
	$(PY) python -m src.transcribe

extract: ## Aplica la rúbrica a cada transcripción con Claude Code (~4 USD, cacheado)
	$(PY) python -m src.extract

annotate: ## Vota por mayoría las anotaciones del panel de tres agentes
	$(PY) python -m src.annotate

analyze: ## Contrasta la familia sobre el consenso del panel y escribe data/public/effects.json
	$(PY) python -m src.analyze --source consenso

anchoring: ## Comprueba que cada positivo del consenso cita una frase de las transcripciones
	$(PY) python -m src.anchoring --source consenso

report: ## Arma results.json y renderiza report/index.html desde data/public/
	$(PY) python -m src.results
	$(PY) python -m src.report

verify: report ## Puerta dura: el informe debe ocupar exactamente 2 páginas
	@"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu \
		--no-pdf-header-footer --print-to-pdf=/tmp/crecere-report.pdf \
		"file://$(CURDIR)/report/index.html" 2>/dev/null
	@n=$$(pdfinfo /tmp/crecere-report.pdf | awk '/^Pages:/{print $$2}'); \
	if [ "$$n" != "2" ]; then \
		echo "FALLO: el informe ocupa $$n páginas, deben ser exactamente 2."; exit 1; \
	else echo "OK: 2 páginas exactas."; fi

test: ## Tests de los helpers estadísticos, el contraste y el anclaje de citas
	$(PY) pytest tests/ -q

lint: ## Formato y linting
	$(PY) ruff format src tests
	$(PY) ruff check src tests

check: lint test ## Todo lo que debe pasar antes de un commit

# clean nunca toca data/: las transcripciones y extracciones no se versionan, costaron
# 18 minutos de GPU y 4 USD, y un clean reflejo las destruiría sin vuelta atrás.
clean: ## Borra cachés de herramientas y el HTML generado
	rm -rf .pytest_cache .ruff_cache report/index.html
