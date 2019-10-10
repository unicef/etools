from abc import ABC

from django.db import transaction
from django.db.models.fields.related_descriptors import ForwardManyToOneDescriptor, ManyToManyDescriptor

from model_utils.tracker import DescriptorWrapper

from etools.applications.core.util_scripts import set_country


class ABCHandler(ABC):

    model = None
    queryset_migration_mapping = ()

    def __init__(self, schema_name=None) -> None:
        if schema_name:
            set_country(schema_name)
        super().__init__()

    def get_instance(self, pk):
        instance = self.model.objects.get(pk=pk)
        print(instance)
        return instance

    def related(self, instance, queryset_migration_mapping):
        for qs, attribute_name in queryset_migration_mapping:
            qs = qs.filter(**{attribute_name: instance})
            if qs.exists():
                print('-------------------------', qs.model.__name__, ' ', qs.count())
                for item in qs:
                    print(item.pk, item)

    def related_instances(self, pk):
        instance = self.get_instance(pk)
        self.related(instance, self.queryset_migration_mapping)

    def merge(self, to_update, to_delete, queryset_migration_mapping):
        with transaction.atomic():
            for qs, attribute_name in queryset_migration_mapping:
                rel_type = getattr(qs.model, attribute_name, None)
                rev_type = getattr(qs.model, attribute_name + '_set', None)
                if not rel_type and rev_type:
                    attribute_name = attribute_name + '_set'
                if isinstance(rel_type, (ForwardManyToOneDescriptor, DescriptorWrapper)):
                    qs.filter(**{attribute_name: to_delete}).update(**{attribute_name: to_update})
                elif isinstance(rel_type, ManyToManyDescriptor):
                    for item in qs.filter(**{attribute_name: to_delete}):
                        related_objects = getattr(item, attribute_name)
                        related_objects.remove(to_delete)
                        related_objects.add(to_update)
                else:
                    print(f'--------------{qs.model}-{rel_type}')

    def merge_instances(self, to_update_pk, to_delete_pk):
        to_update = self.get_instance(to_update_pk)
        to_delete = self.get_instance(to_delete_pk)
        self.merge(to_update, to_delete, self.queryset_migration_mapping)
