APP_NAME = app-glpi
PORT = 8000
DOCKER_COMPOSE = docker-compose
DOCKER_COMPOSE_FILE = docker-compose.yml
DOCKER_COMPOSE_DEV_FILE = docker-compose.dev.yml
PYTHON = python3
VENV_DIR = .venv
VENV_BIN = $(VENV_DIR)/bin
PIP = $(VENV_BIN)/pip

.PHONY: check_deps check_python check_reqs build run stop restart logs clean dev test lint status venv

check_python:
    @which $(PYTHON) > /dev/null || (echo "Python not found. Please install Python 3." && exit 1)
    @$(PYTHON) --version | grep -q "Python 3" || (echo "Python 3 is required." && exit 1)
    @echo "Python 3 is installed."

venv: check_python
    @test -d $(VENV_DIR) || ($(PYTHON) -m venv $(VENV_DIR) && echo "Virtual environment created.")
    @$(PIP) install --upgrade pip

check_reqs: venv
    @test -f requirements.txt || (echo "requirements.txt file not found." && exit 1)
    @$(PIP) list | grep -q "fastapi" || (echo "Installing dependencies..." && $(PIP) install -r requirements.txt)
    @echo "Dependencies checked."

check_deps: check_reqs

build: check_deps
    docker build -t $(APP_NAME) .

run: check_deps
    $(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_FILE) up -d

dev: check_deps
    $(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_DEV_FILE) up

stop:
    $(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_FILE) down

restart: stop run

logs:
    $(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_FILE) logs -f $(APP_NAME)

clean:
    $(DOCKER_COMPOSE) -f $(DOCKER_COMPOSE_FILE) down --volumes --remove-orphans
    docker system prune -f

test: check_deps
    docker run --rm $(APP_NAME) pytest -xvs

lint: check_deps
    docker run --rm $(APP_NAME) flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

status:
    @echo "Containers status:"
    docker ps -a --filter "name=$(APP_NAME)"
    @echo "\nChecking API health:"
    @curl -s http://localhost:$(PORT)/health || echo "API is not responding"