#!/bin/sh
celery -A celery_app worker --loglevel=info --concurrency=2 --without-mingle --without-gossip --without-heartbeat &
uvicorn api:app --host 0.0.0.0 --port 8000