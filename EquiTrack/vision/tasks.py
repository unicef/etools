from celery.utils.log import get_task_logger

from EquiTrack.celery import app
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
def sync():
    processed = []
    for country in Country.objects.filter(vision_sync_enabled=True):
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
        processed.append(country)
    logger.info('Processed the following countries during sync: {}'.format(
        ',\n '.join([country.name for country in processed]))
    )
