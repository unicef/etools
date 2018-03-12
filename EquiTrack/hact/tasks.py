from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import datetime

from django.db import connection

from celery.utils.log import get_task_logger

from EquiTrack.celery import app
from hact.models import AggregateHact
from users.models import Country

logger = get_task_logger(__name__)


@app.task
def update_aggregate_hact_values():
    logger.info('Hact Aggregator Task process started')
    for country in Country.objects.exclude(schema_name='public'):
        connection.set_tenant(country)
        aggregate_hact, _ = AggregateHact.objects.get_or_create(year=datetime.today().year)
        try:
            aggregate_hact.update()
        except Exception as e:
            logger.error(country, e.message)

    logger.info('Hact Aggregator Task process finished')
