# Pipeline del análisis. Cada paso escribe su salida en data/ y es re-ejecutable.
# pyenv exporta VIRTUAL_ENV y confunde a uv; lo quitamos del entorno.
unexport VIRTUAL_ENV
PY := uv run --quiet

# report y verify DEBEN ser .PHONY: existe un directorio report/ y sin esto
# make da 'up to date' y no ejecuta nada, dejando la puerta inservible.
.PHONY: help inventory transcribe test lint check clean report verify

help:  ## Muestra esta ayuda
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

inventory: ## Inventario técnico del corpus (formato, duración, n analizable)
	$(PY) python src/inventory.py

test: ## Tests de los helpers estadísticos
	$(PY) pytest tests/ -q

lint: ## Formato y linting
	$(PY) ruff format src tests
	$(PY) ruff check src tests

check: lint test ## Todo lo que debe pasar antes de un commit

clean: ## Borra salidas derivadas (no toca data/raw)
	rm -rf data/interim/* data/processed/* .pytest_cache .ruff_cache

report: ## Renderiza report/index.html desde data/public/results.json
	$(PY) python -m src.report

verify: report ## Puerta dura: el informe debe ser exactamente 2 páginas
	@"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu \
		--no-pdf-header-footer --print-to-pdf=/tmp/crecere-report.pdf \
		"file://$(CURDIR)/report/index.html" 2>/dev/null
	@n=$$(pdfinfo /tmp/crecere-report.pdf | awk '/^Pages:/{print $$2}'); \
	if [ "$$n" != "2" ]; then \
		echo "FALLO: el informe ocupa $$n páginas, deben ser exactamente 2."; exit 1; \
	else echo "OK: 2 páginas exactas."; fi
