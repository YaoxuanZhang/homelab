.PHONY: up down restart pull logs config ps setup

all: setup up

up:
	DOMAIN_NAME=$$(grep DOMAIN_NAME .env | cut -d '=' -f2) python3 hub/generate_endpoints.py
	docker compose up -d

down:
	docker compose down

down-v:
	docker compose down -v

reset: down-v up

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

setup-cloudflare:
	powershell -ExecutionPolicy Bypass -File ./hub/cloudflared/setup-cloudflare.ps1

setup: setup-cloudflare
