import json
import sys
from abc import ABCMeta, abstractmethod

from django.conf import settings
from django.db import connection
from django.utils import six

import requests
from celery.utils.log import get_task_logger
from django.utils.encoding import force_text

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
            raise VisionException('You must set the ENDPOINT name')

        separator = '' if self.URL.endswith('/') else '/'

        self.url = '{}{}{}'.format(self.URL, separator, endpoint)
        if country:
            self.url += '/{}'.format(country.business_area_code)

        logger.info('About to get data from {}'.format(self.url))

    def get(self):
        response = requests.get(
            self.url,
            headers={'Content-Type': 'application/json'},
            auth=(settings.VISION_USER, settings.VISION_PASSWORD),
            verify=False
        )

        if response.status_code != 200:
            raise VisionException('Load data failed! Http code: {}'.format(response.status_code))
        json_response = response.json()
        if json_response == VISION_NO_DATA_MESSAGE:
            return []

        return json_response


class FileDataLoader(object):

    def __init__(self, filename=None):
        if filename is None:
            raise Exception('You need provide the path to the file')

        self.filename = filename

    def get(self):
        data = json.load(open(self.filename))
        return data


class DataSynchronizer(object):

    __metaclass__ = ABCMeta

    REQUIRED_KEYS = {}
    GLOBAL_CALL = False
    LOADER_CLASS = None
    LOADER_EXTRA_KWARGS = []

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

        return [rec for rec in records if is_valid_record(rec)]

    def sync(self):
        """
        Performs the database sync
        :return:
        """
        log = VisionSyncLog(
            country=self.country,
            handler_name=self.__class__.__name__
        )

        loader_kwargs = self._get_kwargs()
        loader_kwargs.update({
            kwarg_name: getattr(self, kwarg_name)
            for kwarg_name in self.LOADER_EXTRA_KWARGS
        })
        data_getter = self.LOADER_CLASS(**loader_kwargs)

        try:
            original_records = data_getter.get()
            logger.info('{} records returned from get'.format(len(original_records)))

            converted_records = self._convert_records(original_records)
            log.total_records = len(converted_records)
            logger.info('{} records returned from conversion'.format(len(converted_records)))

            totals = self._save_records(converted_records)

        except Exception as e:
            logger.info('sync', exc_info=True)
            log.exception_message = force_text(e)
            traceback = sys.exc_info()[2]
            six.reraise(VisionException, VisionException(force_text(e)), traceback)
        else:
            if isinstance(totals, dict):
                log.total_processed = totals.get('processed', 0)
                log.details = totals.get('details', '')
                log.total_records = totals.get('total_records', log.total_records)
            else:
                log.total_processed = totals
            log.successful = True
        finally:
            log.save()


class VisionDataSynchronizer(DataSynchronizer):

    ENDPOINT = None
    LOADER_CLASS = VisionDataLoader

    def __init__(self, country=None, *args, **kwargs):
        if not country:
            raise VisionException('Country is required')
        if self.ENDPOINT is None:
            raise VisionException('You must set the ENDPOINT name')

        logger.info('Synchronizer is {}'.format(self.__class__.__name__))

        self.country = country

        connection.set_tenant(country)
        logger.info('Country is {}'.format(country.name))

    def _get_kwargs(self):
        return {
            'country': self.country,
            'endpoint': self.ENDPOINT,
        }


class FileDataSynchronizer(DataSynchronizer):
    LOADER_CLASS = FileDataLoader
    LOADER_EXTRA_KWARGS = ['filename', ]

    def __init__(self, country=None, *args, **kwargs):

        filename = kwargs.get('filename', None)
        if not country:
            raise VisionException('Country is required')
        if not filename:
            raise VisionException('You need provide the path to the file')

        logger.info('Synchronizer is {}'.format(self.__class__.__name__))

        self.filename = filename
        self.country = country
        connection.set_tenant(country)
        logger.info('Country is {}'.format(country.name))

        super(FileDataSynchronizer, self).__init__(country, *args, **kwargs)

    def _get_kwargs(self):
        return {
            'filename': self.filename,
        }
