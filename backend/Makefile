run:
	. .venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port $${PORT:-8005}
fmt:
	. .venv/bin/activate && python -m pip install ruff black && ruff check --fix . && black .
