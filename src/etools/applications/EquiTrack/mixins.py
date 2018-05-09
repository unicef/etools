"""
Project wide mixins for models and classes
"""
from django.db import connection, models, transaction
from django.db.models import Q

from rest_framework import serializers

from etools.applications.EquiTrack.utils import run_on_all_tenants


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


class ModelHavingTenantRelationsMixin(object):
    """
    Mixin for public class that can be related from tenants.
    Cascade removing don't work properly in this case, so we
    need to check schemas in loop and clear connections manually.

    https://github.com/bernardopires/django-tenant-schemas/issues/420
    """
    @transaction.atomic
    def delete(self, *args, **kwargs):
        def clear_relations(obj=None):
            relations = [f for f in obj._meta.get_fields() if f.auto_created and not f.concrete]

            for relation in relations:
                if isinstance(relation, models.ManyToManyRel):
                    # m2m relations should be unlinked
                    relation.through.objects.filter(**{relation.field.m2m_reverse_field_name(): obj}).delete()

                elif isinstance(relation, models.ManyToOneRel) and relation.on_delete == models.CASCADE:
                    # related objects should be removed in loop to perform correct delete behaviour for child
                    for related_obj in getattr(obj, relation.related_name).all():
                        related_obj.delete()

                elif isinstance(relation, models.OneToOneRel) and relation.on_delete == models.CASCADE:
                    if hasattr(obj, relation.related_name):
                        getattr(obj, relation.related_name).delete()

        run_on_all_tenants(clear_relations, obj=self)

        super(ModelHavingTenantRelationsMixin, self).delete(*args, **kwargs)
