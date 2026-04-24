.PHONY: up init down restart reset logs ps health seed migrate build doctor

up:
	docker compose up --build -d

init:
	docker compose up -d db
	docker compose run --rm api alembic upgrade heads
	docker compose run --rm api python -m app.tasks.seed

down:
	docker compose down

restart:
	docker compose down
	docker compose up --build -d

reset:
	docker compose down -v
	docker compose up --build -d
	docker compose run --rm api alembic upgrade heads
	docker compose run --rm api python -m app.tasks.seed

build:
	docker compose build

logs:
	docker compose logs -f --tail=200

ps:
	docker compose ps

migrate:
	docker compose run --rm api alembic upgrade heads

seed:
	docker compose run --rm api python -m app.tasks.seed

health:
	docker compose up -d api
	curl -sS -i http://127.0.0.1:8000/health

doctor:
	docker info > /dev/null
	docker compose ps
	docker compose up -d db api scheduler public_frontend
	curl -sS -i http://127.0.0.1:8000/health
