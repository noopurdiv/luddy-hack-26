DOCKER_COMPOSE ?= docker compose

.PHONY: build up logs down test demo

build:
	$(DOCKER_COMPOSE) build

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
