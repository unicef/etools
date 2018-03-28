from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf import settings
from django.core.cache import cache

from celery.utils.log import get_task_logger

from azure_graph_api.client import azure_sync_users
from EquiTrack.celery import app

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
    url = '{}/{}/users?$top={}'.format(
        settings.AZURE_GRAPH_API_BASE_URL,
        settings.AZURE_GRAPH_API_VERSION,
        settings.AZURE_GRAPH_API_PAGE_SIZE
    )
    azure_sync_users(url)
    logger.info('Azure Complete Sync Process finished')


@app.task
def sync_delta_users():
    logger.info('Azure Delta Sync Process started')
    url = cache.get(
        AZURE_GRAPH_API_USER_CACHE_KEY,
        '{}/{}/users/delta?$top={}'.format(
            settings.AZURE_GRAPH_API_BASE_URL,
            settings.AZURE_GRAPH_API_VERSION,
            settings.AZURE_GRAPH_API_PAGE_SIZE
        )
    )
    delta_link = azure_sync_users(url)
    cache.set(AZURE_GRAPH_API_USER_CACHE_KEY, delta_link)
    logger.info('Azure Delta Sync Process finished')
    return delta_link
