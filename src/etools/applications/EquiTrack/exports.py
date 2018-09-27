from django.db import connection

from rest_framework import serializers


class ExportSerializerMixin(object):
    country = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        self.add_country()
        super(ExportSerializerMixin, self).__init__(*args, **kwargs)

    def add_country(self):
        # Add country to list of fields exported
        if hasattr(self.Meta, "fields") and self.Meta.fields != "__all__":
            self.Meta.fields.append("country")
            if "country" not in self._declared_fields:
                self._declared_fields["country"] = self.country

    def get_country(self, obj):
        return connection.schema_name
