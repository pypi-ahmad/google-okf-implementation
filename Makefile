.PHONY: install lint format typecheck test notebook-validate handbook-pdf check precommit-install run-api run-ui run-cli run-e2e

UV_CACHE_DIR ?= .uv-cache

install:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv sync --extra dev

lint:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run --no-sync ruff check src tests scripts

format:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run --no-sync black src tests scripts

typecheck:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run --no-sync mypy src/enterprise_okf_ai --python-version 3.12

test:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run --no-sync pytest -q

notebook-validate:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run --no-sync python scripts/validate_notebook.py notebooks/tutorial.ipynb

handbook-pdf:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run --no-sync python scripts/build_handbook_pdf.py

check: lint typecheck test notebook-validate

precommit-install:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run --no-sync pre-commit install

run-api:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run --no-sync enterprise-okf-ai serve --host 0.0.0.0 --port 8000

run-ui:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run --no-sync streamlit run src/enterprise_okf_ai/ui/streamlit_app.py

run-cli:
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv run --no-sync enterprise-okf-ai --help

run-e2e:
	PYTHONPATH=src UV_CACHE_DIR=$(UV_CACHE_DIR) uv run --no-sync python scripts/run_real_e2e.py --strict
