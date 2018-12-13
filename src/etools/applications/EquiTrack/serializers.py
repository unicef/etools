import json

from django.db.models import Aggregate, CharField, Value

from rest_framework import serializers


class StringConcat(Aggregate):
    """ A custom aggregation function that returns "," separated strings """

    function = 'GROUP_CONCAT'
    template = '%(function)s(%(distinct)s%(expressions)s)'

    def __init__(self, expression, separator=",", distinct=False, **extra):
        super().__init__(
            expression,
            Value(separator),
            distinct='DISTINCT ' if distinct else '',
            output_field=CharField(),
            **extra
        )

    def as_postgresql(self, compiler, connection):
        self.function = 'STRING_AGG'
        return super().as_sql(compiler, connection)


class JsonFieldSerializer(serializers.Field):

    def to_representation(self, value):
        return json.loads(value) if isinstance(value, str) else value

    def to_internal_value(self, data):
        return json.dumps(data) if isinstance(data, dict) else data
