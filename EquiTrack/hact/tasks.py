from datetime import datetime

from django.db import connection

from celery.utils.log import get_task_logger
from hact.models import AggregateHact

from EquiTrack.celery import app
from users.models import Country

logger = get_task_logger(__name__)


@app.task
def update_aggregate_hact_values():
    for country in Country.objects.exclude(schema_name='public'):
        connection.set_tenant(country)
        aggregate_hact, _ = AggregateHact.objects.get_or_create(year=datetime.today().year)
        try:
            aggregate_hact.update()
        except Exception as e:
            logger.error(country, e.message)
