# Pipeline del análisis. Cada paso escribe su salida en data/ y es re-ejecutable.
# pyenv exporta VIRTUAL_ENV y confunde a uv; lo quitamos del entorno.
unexport VIRTUAL_ENV
PY := uv run --quiet

.PHONY: help inventory test lint check clean

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
