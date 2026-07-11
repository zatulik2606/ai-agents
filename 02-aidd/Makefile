.PHONY: install run

install:
	uv sync

run: install
	PYTHONPATH=src uv run python -m nika.main
