import sys
from abc import ABCMeta, abstractmethod

from django.conf import settings
from django.db import connection

import requests
from celery.utils.log import get_task_logger

from vision.exceptions import VisionException
from vision.models import VisionSyncLog

logger = get_task_logger('vision.synchronize')

# VISION_NO_DATA_MESSAGE is what the remote vision system returns when it has no data
VISION_NO_DATA_MESSAGE = 'No Data Available'


class VisionDataLoader(object):
    # Caveat - this loader probably doesn't construct a correct URL when the synchronizer's GLOBAL_CALL = True).
    # See https://github.com/unicef/etools/issues/1098
    URL = settings.VISION_URL

    def __init__(self, country=None, endpoint=None):
        if endpoint is None:
            raise VisionException(message='You must set the ENDPOINT name')

        separator = '' if self.URL.endswith('/') else '/'

        self.url = '{}{}{}'.format(self.URL, separator, endpoint)
        if country:
            self.url += '/{}'.format(country.business_area_code)

    def get(self):
        response = requests.get(
            self.url,
            headers={'Content-Type': 'application/json'},
            auth=(settings.VISION_USER, settings.VISION_PASSWORD),
            verify=False
        )

        if response.status_code != 200:
            raise VisionException(
                message=('Load data failed! Http code: {}'.format(response.status_code))
            )
        json_response = response.json()
        if json_response == VISION_NO_DATA_MESSAGE:
            return []

        return json_response


class VisionDataSynchronizer(object):

    __metaclass__ = ABCMeta

    ENDPOINT = None
    REQUIRED_KEYS = {}
    GLOBAL_CALL = False
    LOADER_CLASS = VisionDataLoader
    LOADER_EXTRA_KWARGS = []

    def __init__(self, country=None):
        if not country:
            raise VisionException(message='Country is required')
        if self.ENDPOINT is None:
            raise VisionException(message='You must set the ENDPOINT name')

        logger.info('Synchronizer is {}'.format(self.__class__.__name__))

        self.country = country

        connection.set_tenant(country)
        logger.info('Country is {}'.format(country.name))

    @abstractmethod
    def _convert_records(self, records):
        pass

    @abstractmethod
    def _save_records(self, records):
        pass

    def _filter_records(self, records):
        def is_valid_record(record):
            for key in self.REQUIRED_KEYS:
                if key not in record:
                    return False
            return True

        return filter(is_valid_record, records)

    def sync(self):
        """
        Performs the database sync
        :return:
        """
        log = VisionSyncLog(
            country=self.country,
            handler_name=self.__class__.__name__
        )

        loader_kwargs = {
            'country': self.country,
            'endpoint': self.ENDPOINT,
        }
        loader_kwargs.update({
            kwarg_name: getattr(self, kwarg_name)
            for kwarg_name in self.LOADER_EXTRA_KWARGS
        })
        data_getter = self.LOADER_CLASS(**loader_kwargs)
        logger.info('About to get data from {}'.format(data_getter.url))
        try:
            original_records = data_getter.get()
            logger.info('{} records returned from get'.format(len(original_records)))

            converted_records = self._convert_records(original_records)
            log.total_records = len(converted_records)
            logger.info('{} records returned from conversion'.format(len(converted_records)))

            totals = self._save_records(converted_records)

        except Exception as e:
            logger.info('sync caught {} with message "{}"'.format(type(e).__name__, e.message))
            log.exception_message = e.message
            raise VisionException(message=e.message), None, sys.exc_info()[2]
        else:
            if isinstance(totals, dict):
                log.total_processed = totals.get('processed', 0)
                log.details = totals.get('details', None)
                log.total_records = totals.get('total_records', log.total_records)
            else:
                log.total_processed = totals
            log.successful = True
        finally:
            log.save()
