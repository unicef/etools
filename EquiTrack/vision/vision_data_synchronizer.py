
from django.db import connection
from django.conf import settings

from abc import ABCMeta, abstractmethod

import requests
from celery.utils.log import get_task_logger

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

    def __init__(self, country=None):
        if not country:
            raise VisionException(message='Country is required')
        if self.ENDPOINT is None:
            raise VisionException(message='You must set the ENDPOINT name')

        self.county = country
        self.url = '{}/{}/{}'.format(
            self.URL,
            self.ENDPOINT,
            country.business_area_code
        )
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
        try:
            original_records = self._load_records()
            converted_records = self._convert_records(original_records)
            logger.info('Processing {} records'.format(len(original_records)))
            self._save_records(converted_records)
        except Exception as e:
            raise VisionException(message=e.message)

