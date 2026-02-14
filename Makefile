.PHONY: up down restart pull logs config ps

# Default target
all: up

up:
	@docker network inspect gateway_nw >/dev/null 2>&1 || docker network create gateway_nw
	docker compose up -d

down:
	docker compose down

down-v:
	docker compose down -v

restart:
	docker compose restart

pull:
	docker compose pull

logs:
	docker compose logs -f

config:
	docker compose config

ps:
	docker compose ps
