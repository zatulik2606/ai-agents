.PHONY: install run run-mcp-nika docker-build docker-run dataset dataset-upload
.PHONY: test-deterministic test-llm-judge test-all

install:
	uv sync --python 3.12

run: install
	PYTHONPATH=src uv run python -m nika.main

# MCP-сервер Ники (streamable-http :8000). Запускать до бота для полного набора tools.
# Terminal 1: make run-mcp-nika
# Terminal 2: make run
run-mcp-nika:
	cd mcp/mcp-nika-agent && uv sync --python 3.12 && uv run python -m mcp_nika_agent

dataset:
	PYTHONPATH=src uv run python -m nika.services.dataset_synthesizer --create

dataset-upload:
	PYTHONPATH=src uv run python -m nika.services.dataset_synthesizer --upload

# E2E trajectory-тесты агента (agentevals). См. docs/vision.md §18.
test-deterministic: install
	PYTHONPATH=src uv run pytest tests/test_agent_deterministic.py -v

test-llm-judge: install
	PYTHONPATH=src uv run pytest tests/test_agent_llm_judge.py -v

test-all: install
	PYTHONPATH=src uv run pytest tests/ -v

docker-build:
	docker build -t nika-bot .

docker-run: docker-build
	docker run --rm --env-file .env -v "$(PWD)/data:/app/data" nika-bot
