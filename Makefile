.PHONY: install dev test

install:            ## crea l'ambiente Python del backend e installa le dipendenze
	cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
	cd backend && [ -f .env ] || cp .env.example .env

dev:                ## avvia il backend su http://localhost:8000 (ricarica a ogni modifica)
	cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

test:               ## esegue i test del backend
	cd backend && .venv/bin/python -m pytest -q
