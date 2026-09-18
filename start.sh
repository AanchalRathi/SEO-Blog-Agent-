#!/bin/sh
celery -A celery_app worker --loglevel=info &
uvicorn api:app --host 0.0.0.0 --port 8000