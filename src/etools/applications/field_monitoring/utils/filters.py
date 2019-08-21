from django.db.models import Subquery

from django_filters import BaseCSVFilter


class M2MInFilter(BaseCSVFilter):
    """Optimized m2m filtering without distinct using subquery"""

    def filter(self, qs, value):
        if not value:
            return qs

        assert hasattr(self.model, self.field_name), "wrong field_name passed. this can be caused by typo or trying " \
                                                     "to use nested fields (only one level of relations is supported " \
                                                     "for now)"

        relation = getattr(self.model, self.field_name)

        def get_relation_name(model):
            return '{}_{}'.format(model._meta.model_name, model._meta.auto_field.name)

        qs = qs.filter(pk__in=Subquery(
            relation.through.objects.filter(**{
                '{}__in'.format(get_relation_name(relation.field.related_model)): value
            }).values_list(get_relation_name(relation.field.model), flat=True)
        ))
        return qs
