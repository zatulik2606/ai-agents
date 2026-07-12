.PHONY: install run docker-build docker-run

install:
	uv sync

run: install
	PYTHONPATH=src uv run python -m nika.main

docker-build:
	docker build -t nika-bot .

docker-run: docker-build
	docker run --rm --env-file .env -v "$(PWD)/data:/app/data" nika-bot
