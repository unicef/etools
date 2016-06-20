import datetime

from django.db import connection

from celery.utils.log import get_task_logger

from EquiTrack.celery import app, send_to_slack
from users.models import Country
from vision_data_synchronizer import VisionException
from vision.adapters.programme import ProgrammeSynchronizer, RAMSynchronizer
from vision.adapters.partner import PartnerSynchronizer
from vision.adapters.funding import (
    FundingSynchronizer,
    DCTSynchronizer,
)

SYNC_HANDLERS = [
    ProgrammeSynchronizer,
    RAMSynchronizer,
    PartnerSynchronizer,
    FundingSynchronizer,
    #DCTSynchronizer
]


logger = get_task_logger(__name__)


@app.task
def sync(country_name=None):
    processed = []
    countries = Country.objects.filter(vision_sync_enabled=True)
    if country_name is not None:
        countries.filter(name=country_name)
    for country in countries:
        connection.set_tenant(country)
        for handler in SYNC_HANDLERS:
            try:
                logger.info('Starting vision sync handler {} for country {}'.format(
                    handler.__name__, country.name
                ))
                handler(country).sync()
                logger.info("{} sync successfully".format(handler.__name__))

            except VisionException as e:
                logger.error("{} sync failed, Reason: {}".format(
                    handler.__name__, e.message
                ))
        country.vision_last_synced = datetime.datetime.now()
        country.save()
        processed.append(country)

    text = 'Processed the following countries during sync: {}'.format(
        ',\n '.join([country.name for country in processed])
    )
    send_to_slack(text)
    logger.info(text)
