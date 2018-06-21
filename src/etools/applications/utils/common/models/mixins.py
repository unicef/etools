from django.db import models, transaction
from model_utils.managers import InheritanceManager

from etools.applications.utils.common.utils import run_on_all_tenants


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


class InheritedModelMixin(object):
    """
    Mixin for easier access to subclasses. Designed to be tightly used with InheritanceManager
    """

    def get_subclass(self):
        if not self.pk:
            return self

        manager = self._meta.model._default_manager
        if not isinstance(manager, InheritanceManager):
            return self

        return manager.get_subclass(pk=self.pk)
