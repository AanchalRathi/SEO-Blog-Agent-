import os
from dotenv import load_dotenv
from celery import Celery

load_dotenv()

redis_url = os.getenv("REDIS_URL")

celery_app = Celery(
    "seoblog_agent",
    broker=redis_url,
    backend=redis_url,   # same Redis instance stores task results too
    include=["tasks"]    # module where actual task functions will live
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kolkata",
    enable_utc=True,
)