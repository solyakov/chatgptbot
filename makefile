SHELL := /bin/bash
VENV := .venv

$(VENV):
	python -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r requirements.txt

dev: $(VENV)
	$(VENV)/bin/python -m bot

up:
	docker compose up --build -d

ps:
	docker compose ps

logs:
	docker compose logs -f

down:
	docker compose down --remove-orphans

clean:
	rm -rf $(VENV)
	find -type d -name __pycache__ -exec rm -r {} +
	find -type f -name "*.pyc" -delete