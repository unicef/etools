"""
Project wide mixins for models and classes
"""
from django.db import connection
from django.db.models import Q

from rest_framework import serializers


class ExportModelMixin(object):
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
        context = super(ExportModelMixin, self).get_renderer_context()
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


class QueryStringFilterMixin(object):

    def filter_params(self, filters):
        queries = []
        for param_filter, query_filter in filters:
            if param_filter in self.request.query_params:
                value = self.request.query_params.get(param_filter)
                if query_filter.endswith(('__in')):
                    value = value.split(',')
                queries.append(Q(**{query_filter: value}))
        return queries

    def search_params(self, filters, param_name='search'):
        search_term = self.request.query_params.get(param_name)
        search_query = Q()
        if param_name in self.request.query_params:
            for param_filter in filters:
                q = Q(**{param_filter: search_term})
                search_query = search_query | q
        return search_query
