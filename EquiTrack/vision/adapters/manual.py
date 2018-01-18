from __future__ import absolute_import, division, print_function, unicode_literals

import json
import logging
from collections import OrderedDict

from django.db import connection
from django.utils import six

from vision.exceptions import VisionException
from vision.utils import wcf_json_date_as_datetime
from vision.vision_data_synchronizer import VisionDataLoader, VisionDataSynchronizer

logger = logging.getLogger(__name__)


class ManualDataLoader(VisionDataLoader):
    """
    Can be used to sync single objects from VISION
    url templates:
    /endpoint if no country or object_number
    /endpoint/country if no object number provided
    /endpoint/object_number else
    """
    def __init__(self, country=None, endpoint=None, object_number=None):
        if not object_number:
            super(ManualDataLoader, self).__init__(country=country, endpoint=endpoint)
        else:
            if endpoint is None:
                raise VisionException(message='You must set the ENDPOINT name')

            self.url = '{}/{}/{}'.format(
                self.URL,
                endpoint,
                object_number
            )


class MultiModelDataSynchronizer(VisionDataSynchronizer):
    MODEL_MAPPING = {}
    MAPPING = OrderedDict()
    DATE_FIELDS = []

    def _convert_records(self, records):
        if isinstance(records, list):
            return records
        return json.loads(records)

    def _save_records(self, records):
        processed = 0

        filtered_records = self._filter_records(records)

        def _get_field_value(field_name, field_json_code, json_item, model):
            if field_json_code in self.DATE_FIELDS:
                return wcf_json_date_as_datetime(json_item[field_json_code])
            elif field_name in self.MODEL_MAPPING:
                related_model = self.MODEL_MAPPING[field_name]
                reversed_dict = {v: k for k, v in six.iteritems(self.MAPPING[field_name])}
                return related_model.objects.get(**{
                    reversed_dict[field_json_code]: json_item.get(field_json_code, None)
                })
            return json_item[field_json_code]

        def _process_record(json_item):
            try:
                for model_name, model in six.iteritems(self.MODEL_MAPPING):
                    mapped_item = {
                        field_name: _get_field_value(field_name, field_json_code, json_item, model)
                        for field_name, field_json_code in six.iteritems(self.MAPPING[model_name])
                    }
                    kwargs = {
                        field_name: value
                        for field_name, value in six.iteritems(mapped_item)
                        if model._meta.get_field(field_name).unique
                    }

                    if not kwargs:
                        for fields in model._meta.unique_together:
                            if all(field in mapped_item for field in fields):
                                unique_fields = fields
                                break

                        kwargs = {
                            field: mapped_item[field] for field in unique_fields
                        }

                    defaults = {
                        field_name: value
                        for field_name, value in six.iteritems(mapped_item)
                        if field_name not in kwargs
                    }
                    model.objects.update_or_create(
                        defaults=defaults, **kwargs
                    )
            except Exception:
                logger.warning("Exception processing record", exc_info=True)

        for record in filtered_records:
            _process_record(record)
            processed += 1
        return processed


class ManualVisionSynchronizer(MultiModelDataSynchronizer):
    LOADER_CLASS = ManualDataLoader
    LOADER_EXTRA_KWARGS = ['object_number', ]

    def __init__(self, country=None, object_number=None):
        self.object_number = object_number

        if not object_number:
            super(MultiModelDataSynchronizer, self).__init__(country=country)
        else:
            if self.ENDPOINT is None:
                raise VisionException('You must set the ENDPOINT name')

            self.country = country

            connection.set_tenant(country)
            logger.info('Country is {}'.format(country.name))
