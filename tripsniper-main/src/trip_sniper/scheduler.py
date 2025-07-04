from __future__ import annotations

import os
from celery import Celery
from celery.schedules import crontab

from . import pipeline

# Celery application configured with Redis broker
BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
app = Celery("trip_sniper", broker=BROKER_URL)

# Optional cron expression for pipeline execution
RUN_PIPELINE_CRON = os.getenv("RUN_PIPELINE_CRON")


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs) -> None:
    """Register periodic tasks."""
    cron_expr = RUN_PIPELINE_CRON
    if cron_expr:
        fields = cron_expr.split()
        if len(fields) != 5:
            raise ValueError("RUN_PIPELINE_CRON must have 5 fields")
        schedule = crontab(
            minute=fields[0],
            hour=fields[1],
            day_of_month=fields[2],
            month_of_year=fields[3],
            day_of_week=fields[4],
        )
    else:
        schedule = crontab(minute=0, hour="*")
    sender.add_periodic_task(
        schedule,
        run_pipeline_task.s(origin=os.getenv("ORIGIN_IATA", "WAW")),
        name="run pipeline",
    )


@app.task(bind=True, max_retries=3, default_retry_delay=300, acks_late=True)
def run_pipeline_task(self, origin: str | None = None) -> None:
    """Run the data pipeline. Idempotent due to upserts."""
    try:
        pipeline.run(origin=origin)
    except Exception as exc:  # noqa: BLE001
        raise self.retry(exc=exc)
