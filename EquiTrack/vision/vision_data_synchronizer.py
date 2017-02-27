import sys

from django.db import connection
from django.conf import settings

from abc import ABCMeta, abstractmethod

import requests
from celery.utils.log import get_task_logger

from .models import VisionSyncLog

logger = get_task_logger('vision.synchronize')


class VisionException(Exception):
    def __init__(self, message=''):
        super(VisionException, self).__init__(message)


class VisionDataSynchronizer:

    __metaclass__ = ABCMeta

    ENDPOINT = None
    URL = settings.VISION_URL
    NO_DATA_MESSAGE = u'No Data Available'
    REQUIRED_KEYS = {}
    GLOBAL_CALL = False

    def __init__(self, country=None):
        if not country:
            raise VisionException(message='Country is required')
        if self.ENDPOINT is None:
            raise VisionException(message='You must set the ENDPOINT name')

        self.county = country
        self.url = '{}/{}'.format(
            self.URL,
            self.ENDPOINT
        )
        if not self.GLOBAL_CALL:
            self.url += '/{}'.format(country.business_area_code)

        logger.info("Vision sync url:%s" % self.url)
        connection.set_tenant(country)
        logger.info('Country is {}'.format(country.name))

    @abstractmethod
    def _convert_records(self, records):
        pass

    @abstractmethod
    def _save_records(self, records):
        pass

    def _get_json(self, data):
        return [] if data == self.NO_DATA_MESSAGE else data

    def _filter_records(self, records):
        def is_valid_record(record):
            for key in self.REQUIRED_KEYS:
                if key not in record:
                    return False
            return True

        return filter(is_valid_record, records)

    def _load_records(self):
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

        return self._get_json(response.json())

    def sync(self):
        """
        Performs the database sync
        :return:
        """
        log = VisionSyncLog(
            country=self.county,
            handler_name=self.__class__.__name__
        )
        try:
            original_records = self._load_records()
            converted_records = self._convert_records(original_records)
            log.total_records = len(converted_records)
            logger.info('Processing {} records'.format(len(converted_records)))
            log.total_processed = self._save_records(converted_records)
            log.successful = True
        except Exception as e:
            log.exception_message = e.message
            raise VisionException(message=e.message), None, sys.exc_info()[2]
        finally:
            log.save()

