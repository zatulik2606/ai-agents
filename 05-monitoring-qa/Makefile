.PHONY: install run docker-build docker-run dataset dataset-upload

install:
	uv sync

run: install
	PYTHONPATH=src uv run python -m nika.main

dataset:
	PYTHONPATH=src uv run python -m nika.services.dataset_synthesizer --create

dataset-upload:
	PYTHONPATH=src uv run python -m nika.services.dataset_synthesizer --upload

docker-build:
	docker build -t nika-bot .

docker-run: docker-build
	docker run --rm --env-file .env -v "$(PWD)/data:/app/data" nika-bot
