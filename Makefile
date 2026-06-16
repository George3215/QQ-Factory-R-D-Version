.PHONY: help pycheck test smoke control self-test clean

PYTHON ?= python3
CONTROL_HOST ?= 127.0.0.1
CONTROL_PORT ?= 8787
CONTROL_DB ?= data/dev.sqlite3
CONTROL_URL ?= http://$(CONTROL_HOST):$(CONTROL_PORT)
ADMIN_TOKEN ?= dev-admin-token

help:
	@echo "Loop Farm developer commands"
	@echo ""
	@echo "  make pycheck      Compile all Python modules"
	@echo "  make test         Run unit tests"
	@echo "  make smoke        Run local store smoke test"
	@echo "  make control      Start local control API"
	@echo "  make self-test    Run local agent prerequisite check"
	@echo "  make clean        Remove local caches and data"

pycheck:
	$(PYTHON) -m py_compile \
		control/server.py control/store.py \
		farmctl/cli.py farmctl/http.py \
		agent/cli.py agent/config.py agent/http.py agent/inventory.py agent/runner.py

test:
	$(PYTHON) -m unittest discover -s tests

smoke:
	$(PYTHON) scripts/smoke_store.py

control:
	$(PYTHON) -m control.server \
		--host $(CONTROL_HOST) \
		--port $(CONTROL_PORT) \
		--db $(CONTROL_DB) \
		--admin-token $(ADMIN_TOKEN) \
		--ui apps/control-ui \
		--install-dir install

self-test:
	$(PYTHON) -m agent self-test

clean:
	rm -rf data __pycache__ .pytest_cache .ruff_cache .mypy_cache
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
