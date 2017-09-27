import json
import logging
from collections import OrderedDict

from django.db import connection

from vision.utils import wcf_json_date_as_datetime
from vision.vision_data_synchronizer import VisionDataLoader, VisionException, VisionDataSynchronizer

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
            elif field_name in self.MODEL_MAPPING.keys():
                related_model = self.MODEL_MAPPING[field_name]

                reversed_dict = dict(zip(self.MAPPING[field_name].values(), self.MAPPING[field_name].keys()))
                return related_model.objects.get(**{
                    reversed_dict[field_json_code]: json_item.get(field_json_code, None)
                })
            return json_item[field_json_code]

        def _process_record(json_item):
            try:
                for model_name, model in self.MODEL_MAPPING.items():
                    mapped_item = dict(
                        [(field_name, _get_field_value(field_name, field_json_code, json_item, model))
                         for field_name, field_json_code in self.MAPPING[model_name].items()]
                    )
                    kwargs = dict(
                        [(field_name, value) for field_name, value in mapped_item.items()
                         if model._meta.get_field(field_name).unique]
                    )
                    defaults = dict(
                        [(field_name, value) for field_name, value in mapped_item.items()
                         if field_name not in kwargs.keys()]
                    )
                    obj, created = model.objects.update_or_create(
                        defaults=defaults, **kwargs
                    )
            except Exception as exp:
                    print ("Exception message: {} ")
                    print ("Exception type: {} ")
                    print ("Exception args: {} ".format(
                        exp.message, type(exp).__name__, exp.args
                    ))

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
                raise VisionException(message='You must set the ENDPOINT name')

            self.country = country
            self.url = '{}/{}/{}'.format(
                self.URL,
                self.ENDPOINT,
                object_number
            )

            logger.info("Vision sync url:%s" % self.url)
            connection.set_tenant(country)
