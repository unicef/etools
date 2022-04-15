from django.db import connection

from rest_framework import serializers


class ExportModelMixin:
    def set_labels(self, serializer_fields, model):
        labels = {}
        model_labels = {}
        for f in model._meta.fields:
            model_labels[f.name] = f.verbose_name
        for f in serializer_fields:
            if model_labels.get(f, False):
                labels[f] = model_labels.get(f)
            elif serializer_fields.get(f) and serializer_fields[f].label:
                labels[f] = serializer_fields[f].label
            else:
                labels[f] = f.replace("_", " ").title()
        return labels

    def get_renderer_context(self):
        context = super().get_renderer_context()
        if hasattr(self, "get_serializer_class"):
            serializer_class = self.get_serializer_class()
            serializer = serializer_class()
            serializer_fields = serializer.get_fields()
            model = getattr(serializer.Meta, "model")
            context["labels"] = self.set_labels(
                serializer_fields,
                model
            )
        return context


class ExportSerializerMixin:
    country = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        self.add_country()
        super().__init__(*args, **kwargs)

    def add_country(self):
        # Add country to list of fields exported
        if hasattr(self.Meta, "fields") and self.Meta.fields != "__all__":
            self.Meta.fields.append("country")
            if "country" not in self._declared_fields:
                self._declared_fields["country"] = self.country

    def get_country(self, obj):
        return connection.schema_name


class GetSerializerClassMixin(object):

    def get_serializer_class(self):
        try:
            return self.serializer_action_map[self.action]
        except (KeyError, AttributeError):
            return super().get_serializer_class()
