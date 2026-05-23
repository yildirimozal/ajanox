VENV := .venv
BIN := $(VENV)/bin
PY := $(BIN)/python

.DEFAULT_GOAL := help

help: ## Komutları listele
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

$(PY): ## (iç) venv oluştur
	python3 -m venv $(VENV)

setup: $(PY) ## venv + editable kurulum (tek seferlik)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e '.[dev,web,signing]'

test: ## Testleri çalıştır
	$(PY) -m pytest -q

lint: ## ruff lint (CI'nin ilk adımı)
	$(BIN)/ruff check src/ tests/

fix: ## ruff ile otomatik düzelt
	$(BIN)/ruff check --fix src/ tests/

check: lint test ## lint + test (CI eşdeğeri)

run: ## Terminal shell başlat
	$(BIN)/ajanox

web: ## Web dashboard başlat (http://localhost:8765)
	$(BIN)/ajanox web

clean: ## venv ve cache'leri temizle
	rm -rf $(VENV) .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +

.PHONY: help setup test lint fix check run web clean
