run:
	. .venv/bin/activate && uvicorn app.main:app --reload --port $${PORT:-8000}
fmt:
	. .venv/bin/activate && python -m pip install ruff black && ruff check --fix . && black .
