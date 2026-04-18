DOCKER_COMPOSE ?= docker compose

.PHONY: build up logs down test demo rebuild rebuild-all

build:
	$(DOCKER_COMPOSE) build

# Force fresh UI bundle (fixes “still seeing old frontend” after git pull)
rebuild:
	$(DOCKER_COMPOSE) build --no-cache frontend
	$(DOCKER_COMPOSE) up -d frontend

# Rebuild all images from scratch, then restart stack
rebuild-all:
	$(DOCKER_COMPOSE) build --no-cache
	$(DOCKER_COMPOSE) up -d

up:
	$(DOCKER_COMPOSE) up -d

logs:
	$(DOCKER_COMPOSE) logs -f

down:
	$(DOCKER_COMPOSE) down

test:
	$(DOCKER_COMPOSE) run --rm service_compress pytest tests/ -v

demo:
	@python -m webbrowser -t http://localhost:3000 || true
