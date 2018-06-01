
import json
import logging
import types
from collections import OrderedDict

from django.db import connection
from django.db.models import NOT_PROVIDED

from etools.applications.vision.exceptions import VisionException
from etools.applications.vision.utils import wcf_json_date_as_datetime
from etools.applications.vision.vision_data_synchronizer import VisionDataLoader, VisionDataSynchronizer

logger = logging.getLogger(__name__)


class Empty(object):
    pass


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
                raise VisionException('You must set the ENDPOINT name')
            self.url = '{}/{}/{}'.format(
                self.URL,
                endpoint,
                object_number
            )


class MultiModelDataSynchronizer(VisionDataSynchronizer):
    MODEL_MAPPING = {}
    MAPPING = OrderedDict()
    DATE_FIELDS = []
    DEFAULTS = {}
    FIELD_HANDLERS = {}

    def _convert_records(self, records):
        if isinstance(records, list):
            return records
        try:
            return json.loads(records)
        except ValueError:
            return []

    def _get_field_value(self, field_name, field_json_code, json_item, model):
        result = None

        if field_json_code in self.DATE_FIELDS:
            # parsing field as date
            return wcf_json_date_as_datetime(json_item[field_json_code])
        elif field_name in self.MODEL_MAPPING.keys():
            # this is related model, so we need to fetch somehow related object.
            related_model = self.MODEL_MAPPING[field_name]

            if isinstance(related_model, types.FunctionType):
                # callable provided, object should be returned from it
                result = related_model(data=json_item, key_field=field_json_code)
            else:
                # model class provided, related object can be fetched with query by field
                # analogue of field_json_code
                reversed_dict = dict(zip(
                    self.MAPPING[field_name].values(),
                    self.MAPPING[field_name].keys()
                ))
                result = related_model.objects.get(**{
                    reversed_dict[field_json_code]: json_item.get(field_json_code, None)
                })
        else:
            # field can be used as it is without custom mappings. if field has default, it should be used
            result = json_item.get(field_json_code, Empty)
            if result is Empty:
                # try to get default for field
                field_default = model._meta.get_field(field_name).default
                if field_default is not NOT_PROVIDED:
                    result = field_default

        # additional logic on field may be applied
        value_handler = self.FIELD_HANDLERS.get(
            {y: x for x, y in self.MODEL_MAPPING.items()}.get(model), {}
        ).get(field_name, None)
        if value_handler:
            result = value_handler(result)
        return result

    def _process_record(self, json_item):
        try:
            for model_name, model in self.MODEL_MAPPING.items():
                mapped_item = dict(
                    [(field_name, self._get_field_value(field_name, field_json_code, json_item, model))
                     for field_name, field_json_code in self.MAPPING[model_name].items()]
                )
                kwargs = dict(
                    [(field_name, value) for field_name, value in mapped_item.items()
                     if model._meta.get_field(field_name).unique]
                )

                if not kwargs:
                    for fields in model._meta.unique_together:
                        if all(field in mapped_item.keys() for field in fields):
                            unique_fields = fields
                            break

                    kwargs = {
                        field: mapped_item[field] for field in unique_fields
                    }

                defaults = dict(
                    [(field_name, value) for field_name, value in mapped_item.items()
                     if field_name not in kwargs.keys()]
                )
                defaults.update(self.DEFAULTS.get(model, {}))
                model.objects.update_or_create(
                    defaults=defaults, **kwargs
                )
        except Exception:
            logger.warning('Exception processing record', exc_info=True)

    def _save_records(self, records):
        processed = 0
        filtered_records = self._filter_records(records)

        for record in filtered_records:
            self._process_record(record)
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
