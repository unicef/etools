from celery.schedules import crontab
from celery.task import periodic_task
from celery.utils.log import get_task_logger

from EquiTrack.celery import app
from users.models import Country
from .vision_data_synchronizer import VisionException
from .programme_synchronizer import ProgrammeSynchronizer

SYNC_HANDLERS = [
    ProgrammeSynchronizer
]


logger = get_task_logger(__name__)


@periodic_task(run_every=crontab(minute=0, hour=0))
def sync():
    processed = []
    for country in Country.objects.filter(buisness_area_code__isnull=False):
        for handler in SYNC_HANDLERS:
            try:
                logger.info('Starting vision sync handler {} for country {}'.format(
                    handler.__name__, country.name
                ))
                handler(country).sync()
                logger.info("{} sync successfully".format(handler.__name__))

            except VisionException, e:
                logger.error("{} sync failed, Reason: {}".format(
                    handler.__name__, e.message
                ))
        processed.append(country)
    logger.info('Processed the following countries during sync: {}'.format(
        ', '.join([country.name for country in processed]))
    )
