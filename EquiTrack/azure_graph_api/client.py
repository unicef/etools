from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import requests

from django.conf import settings
from django.core.cache import cache
from azure.common import AzureHttpError

from azure_graph_api.utils import handle_records

logger = logging.getLogger(__name__)
AZURE_GRAPH_API_TOKEN_CACHE_KEY = 'azure_graph_api_token_cache_key'


def get_token():
    """
    generate or retrieve token for azure integration
    base on https://developer.microsoft.com/en-us/graph/docs/concepts/auth_overview
    """
    logger.info('Request for token started')

    token = cache.get(AZURE_GRAPH_API_TOKEN_CACHE_KEY)
    if not token:
        logger.info('Request new token to be generated')
        path = settings.AZURE_TOKEN_URL
        post_dict = {
            'grant_type': 'client_credentials',
            'client_id': settings.AZURE_CLIENT_ID,
            'client_secret': settings.AZURE_CLIENT_SECRET,
            'resource': settings.AZURE_GRAPH_API_BASE_URL
        }
        response = requests.post(path, post_dict)
        if response.status_code == 200:
            jresponse = response.json()
            token = jresponse['access_token']
            # Cache token for 3600 seconds, which matches the default Azure token expiration
            cache.set(AZURE_GRAPH_API_TOKEN_CACHE_KEY, token, 3600)
            logger.info('Token retrieved')
        else:
            logger.error('Error during token retrieval')
            raise AzureHttpError('Error during token retrieval {}'.format(response.status_code), response.status_code)
    return token


def analyse_page(url, access_token):
    """
    analyse the page
    :param url: url to call
    :param access_token: azure access token
    :return: tuple, next page url and delta url
    """
    headers = {'Authorization': 'Bearer {}'.format(access_token)}
    response = requests.get(url, headers=headers)
    jresponse = response.json()
    if response.status_code == 200:
        logger.info('Azure: Information retrieved')
        handle_records(jresponse)
        url = jresponse.get('@odata.nextLink', None)
    else:
        logger.error('Error during synchronization process')
        raise AzureHttpError('Error processing the response {}'.format(response.status_code), response.status_code)
    return url, jresponse.get('@odata.deltaLink', None)


def azure_sync_users(url):
    """
    synchronize users with azure
    :param url: azure endpoint for users
    :return: delta link to use to retrieve delta updates
    """
    access_token = get_token()
    delta_link = None
    while url:
        url, delta_link = analyse_page(url, access_token)
    return delta_link
