import json

from django.db.models import Aggregate, CharField, Value
from django.utils import six

from rest_framework import serializers

from etools.applications.snapshot.utils import create_dict_with_relations, create_snapshot


class StringConcat(Aggregate):
    """ A custom aggregation function that returns "," separated strings """

    function = 'GROUP_CONCAT'
    template = '%(function)s(%(distinct)s%(expressions)s)'

    def __init__(self, expression, separator=",", distinct=False, **extra):
        super(StringConcat, self).__init__(
            expression,
            Value(separator),
            distinct='DISTINCT ' if distinct else '',
            output_field=CharField(),
            **extra
        )

    def as_postgresql(self, compiler, connection):
        self.function = 'STRING_AGG'
        return super(StringConcat, self).as_sql(compiler, connection)


class JsonFieldSerializer(serializers.Field):

    def to_representation(self, value):
        return json.loads(value) if isinstance(value, six.text_type) else value

    def to_internal_value(self, data):
        return json.dumps(data) if isinstance(data, dict) else data


class SnapshotModelSerializer(serializers.ModelSerializer):
    def save(self, **kwargs):
        pre_save = create_dict_with_relations(self.instance)
        super(SnapshotModelSerializer, self).save(**kwargs)
        create_snapshot(self.instance, pre_save, self.context["request"].user)
        return self.instance
