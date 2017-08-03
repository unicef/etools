from django.contrib.contenttypes.fields import GenericRelation, ReverseGenericManyToOneDescriptor
from django.utils.functional import cached_property


def coded_create_reverse_many_to_one_manager(superclass, rel):
    class RelatedManager(superclass):
        def __init__(self, instance=None):
            super(RelatedManager, self).__init__(instance)
            if rel.field.code:
                self.core_filters[rel.field.code_field] = rel.field.code

    return RelatedManager


class CodedReverseManyToOneDescriptor(ReverseGenericManyToOneDescriptor):
    @cached_property
    def related_manager_cls(self):
        return coded_create_reverse_many_to_one_manager(
            super(CodedReverseManyToOneDescriptor, self).related_manager_cls, self.rel
        )


class CodedGenericRelation(GenericRelation):
    code = None
    code_field = None

    def contribute_to_class(self, cls, name, **kwargs):
        super(CodedGenericRelation, self).contribute_to_class(cls, name, **kwargs)

        setattr(cls, self.name, CodedReverseManyToOneDescriptor(self.remote_field))

    def __init__(self, *args, **kwargs):
        self.code = kwargs.pop('code', self.code)
        self.code_field = kwargs.pop('code_field', 'code')

        super(CodedGenericRelation, self).__init__(*args, **kwargs)
