from django.core import exceptions
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _

from jsonschema import exceptions as jsonschema_exceptions, validate


@deconstructible
class JSONSchemaValidator:
    message = _("Invalid JSON: %(value)s")
    code = 'invalid_json'

    def __init__(self, json_schema, message=None):
        self.json_schema = json_schema
        if message:
            self.message = message

    def __call__(self, value):
        try:
            validate(value, self.json_schema)
        except jsonschema_exceptions.ValidationError as e:
            raise exceptions.ValidationError(self.message, code=self.code, params={'value': e.message})

    def __eq__(self, other):
        return isinstance(other, self.__class__) and \
            self.json_schema == other.json_schema and \
            self.message == other.message and \
            self.code == other.code
