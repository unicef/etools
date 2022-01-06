from django.conf import settings
from django.core.cache import cache
from django.utils.encoding import force_str

import requests
from celery.utils.log import get_task_logger
from unicef_vision.exceptions import VisionException

from etools.applications.users.models import Country
from etools.applications.vision.models import VisionSyncLog
from etools.config.celery import app
from etools.libraries.azure_graph_api.client import azure_sync_users, get_token
from etools.libraries.azure_graph_api.utils import handle_record

logger = get_task_logger(__name__)

AZURE_GRAPH_API_USER_CACHE_KEY = 'azure_graph_api_user_cache_key'


@app.task
def sync_user(username):
    logger.info('Azure Sync User started for %s', username)
    url = '{}/{}/users/{}'.format(
        settings.AZURE_GRAPH_API_BASE_URL,
        settings.AZURE_GRAPH_API_VERSION,
        username
    )
    azure_sync_users(url)
    logger.info('User %s synchronized', username)


@app.task
def sync_all_users():
    logger.info('Azure Complete Sync Process started')
    log = VisionSyncLog.objects.create(country=Country.objects.get(schema_name="public"), handler_name='UserADSync')
    try:
        url = '{}/{}/users?$top={}'.format(
            settings.AZURE_GRAPH_API_BASE_URL,
            settings.AZURE_GRAPH_API_VERSION,
            settings.AZURE_GRAPH_API_PAGE_SIZE
        )
        status, _ = azure_sync_users(url)
    except Exception as e:
        log.exception_message = force_str(e)
        logger.exception(force_str(e))
        raise VisionException(*e.args)
    else:
        log.total_records = status['processed'] + status['skipped']
        log.total_processed = status['processed']
        log.successful = status['created'] + status['updated']
    finally:
        log.save()
    logger.info('Azure Complete Sync Process finished')


@app.task
def sync_delta_users():
    logger.info('Azure Delta Sync Process started')
    log = VisionSyncLog.objects.create(
        country=Country.objects.get(schema_name="public"), handler_name='UserADSyncDelta')
    try:
        url = cache.get(
            AZURE_GRAPH_API_USER_CACHE_KEY,
            '{}/{}/users/delta?$top={}'.format(
                settings.AZURE_GRAPH_API_BASE_URL,
                settings.AZURE_GRAPH_API_VERSION,
                settings.AZURE_GRAPH_API_PAGE_SIZE
            )
        )
        status, delta_link = azure_sync_users(url)
        cache.set(AZURE_GRAPH_API_USER_CACHE_KEY, delta_link)

    except Exception as e:
        log.exception_message = force_str(e)
        logger.exception(force_str(e))
        raise VisionException(*e.args)
    else:
        log.total_records = status['processed'] + status['skipped']
        log.total_processed = status['processed']
        log.successful = True
    finally:
        log.save()
    logger.info('Azure Delta Sync Process finished')
    return delta_link


@app.task
def retrieve_user_info(username):
    logger.info('Azure Delta Sync Process started')
    url = '{}/{}/users/{}'.format(
        settings.AZURE_GRAPH_API_BASE_URL,
        settings.AZURE_GRAPH_API_VERSION,
        username
    )
    access_token = get_token()
    logger.info('User %s synchronized', username)
    headers = {'Authorization': 'Bearer {}'.format(access_token)}
    response = requests.get(url, headers=headers)
    jresponse = response.json()
    if response.status_code == 200:
        logger.info('Azure: Information retrieved')
        return handle_record(jresponse)[-1]
    return {}
