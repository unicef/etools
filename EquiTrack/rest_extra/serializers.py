from __future__ import absolute_import, division, print_function, unicode_literals

from collections import OrderedDict

from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction
from django.db.models.fields import related, related_descriptors
from django.utils import six
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.fields import get_attribute
from rest_framework.serializers import SerializerMetaclass
from rest_framework.validators import BaseUniqueForValidator, UniqueTogetherValidator, UniqueValidator

from utils.common.models.fields import CodedGenericRelation
from utils.common.serializers.mixins import PkSerializerMixin
from utils.common.utils import pop_keys


@six.add_metaclass(SerializerMetaclass)
class DeletableSerializerMixin(object):
    """
    Mixin that allow delete object from list through partial update.
    `_delete` field is used to mark object for delete.
    """
    _delete = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        delete_field = '_delete'

    @property
    def _delete_field(self):
        """
        Shortcut for `_delete` field.
        :return: `_delete` field.
        """
        field = self.fields.get(self.Meta.delete_field, None)

        if field:
            assert len(field.source_attrs) == 1

        return field

    def get_field_names(self, declared_fields, info):
        field_names = super(DeletableSerializerMixin, self).get_field_names(declared_fields, info)
        if isinstance(self.parent, serializers.ListSerializer):
            # Add `_delete` field to fields list. So we don't need to declare it in every subclass.
            field_names = list(field_names) + [self.Meta.delete_field]
        return field_names

    def create(self, validated_data):
        if self._delete_field and validated_data.pop(self._delete_field.source, False):
            raise serializers.ValidationError({self.Meta.delete_field: [_('You can\'t delete not exist object.')]})

        return super(DeletableSerializerMixin, self).create(validated_data)

    def update(self, instance, validated_data):
        if self._delete_field and validated_data.pop(self._delete_field.source, False):
            instance.delete()
            return None

        return super(DeletableSerializerMixin, self).update(instance, validated_data)


class WritableListSerializer(serializers.ListSerializer):
    """
    List serializer that allow modify nested objects including creation and deleting.
    """
    @method_decorator(transaction.atomic)
    def update(self, instance, validated_data):
        if isinstance(instance, models.Manager):
            instance = instance.all()
        exists_instances = {i.pk: i for i in instance}
        excess_instances_pks = set(exists_instances.keys())

        model = self.child.Meta.model

        result = list()
        errors = list()
        has_error = False
        for data in validated_data:
            errors.append(dict())

            # PK used to detect exists objects.
            try:
                pk = get_attribute(data, self.child.pk_field.source_attrs)
            except KeyError:
                pk = None

            try:

                if pk:
                    if pk not in exists_instances:
                        raise serializers.ValidationError({
                            self.child.pk_field.field_name: _('{} with pk `{}` doesn\'t exists.').format(
                                model._meta.verbose_name.title(), pk),
                        })

                    if pk not in excess_instances_pks:
                        raise serializers.ValidationError({
                            self.child.pk_field.field_name: _('Duplication {} with pk `{}`.').format(
                                model._meta.verbose_name, pk)
                        })
                    excess_instances_pks.remove(pk)

                    result.append(self.child.update(exists_instances[pk], data))
                else:
                    result.append(self.child.create(data))

            except serializers.ValidationError as exc:
                has_error = True
                errors[-1] = serializers.as_serializer_error(exc)

        if has_error:
            raise serializers.ValidationError(errors)

        if excess_instances_pks and not getattr(self.root, 'partial', False):
            model._default_manager.filter(pk__in=excess_instances_pks).delete()

        return result


class WritableNestedChildSerializerMixin(PkSerializerMixin):
    """
    Mixin that allow serializer to create and modify related data as nested serializer.
    """
    class Meta:
        list_serializer_class = WritableListSerializer

    def bind(self, field_name, parent):
        super(PkSerializerMixin, self).bind(field_name, parent)

        # For many nested objects we need to determine each object. For is we use pk.
        # So we need to allow client to send it.
        if isinstance(self.parent, self.Meta.list_serializer_class):
            self.pk_field.read_only = False
            self.pk_field.required = False

    def _divide_deferred_validators(self, fields):
        """
        Remove validation that require instance and save for subsequent use.

        Validators like UniqueValidator require instance for correct working.
        So this validators must be called on the stage when instance is available.
        """
        for field in fields.values():
            i = 0

            while i < len(field.validators):
                validator = field.validators[i]
                if not isinstance(validator, (UniqueValidator, UniqueTogetherValidator, BaseUniqueForValidator)):
                    i += 1
                    continue

                if not hasattr(field, '_deferred_validators'):
                    field._deferred_validators = []

                field._deferred_validators.append(validator)
                field.validators.remove(validator)

    def to_internal_value(self, data):
        self._divide_deferred_validators(self.fields)
        return super(WritableNestedChildSerializerMixin, self).to_internal_value(data)

    def _run_deferred_validators(self, instance, data):
        """
        Use validators saved in `_divide_deferred_validators` method.
        """
        errors = {}
        for field_name, field in self.fields.items():
            if not hasattr(field, '_deferred_validators'):
                continue

            value = data.get(field_name)
            if not value:
                continue

            for validator in field._deferred_validators:
                if hasattr(validator, 'set_context'):
                    validator.set_context(field)

                if hasattr(validator, 'instance') and not validator.instance:
                    validator.instance = instance

                try:
                    validator(value)
                except serializers.ValidationError as exc:
                    errors[field.field_name] = exc.detail

        if errors:
            raise serializers.ValidationError(errors)

    def create(self, validation_data):
        # We can create child instance through partial update of parent instance.
        # In this case validation allow to skip required fields and we create instance without these fields.
        # To avoid this we make additional validation for required fields.
        if getattr(self.root, 'partial', False):
            fields = self._writable_fields
            errors = dict()
            for field in fields:
                if field.required and field.field_name not in validation_data:
                    try:
                        field.fail('required')
                    except serializers.ValidationError as exc:
                        errors[field.field_name] = exc.detail

            if errors:
                raise serializers.ValidationError(errors)

        self._run_deferred_validators(None, validation_data)

        return super(WritableNestedChildSerializerMixin, self).create(validation_data)

    def update(self, instance, validation_data):
        self._run_deferred_validators(instance, validation_data)

        return super(WritableNestedChildSerializerMixin, self).update(instance, validation_data)


class WritableNestedParentSerializerMixin(object):
    """
    Serializer that allow to create and update nested objects.
    """
    @property
    def writable_nested_serializers(self):
        return [field_name for field_name, field in self.fields.items()
                if isinstance(field, serializers.BaseSerializer) and not field.read_only]

    def _get_related_model_field(self, nested_serializer):
        """
        Return model field through that nested serializer relate with parent and type of relation.
        :param nested_serializer:
        :return: Tuple contained model field and relation type (`forward`, `reverse`).
        """
        assert len(nested_serializer.source_attrs) == 1, "We doesn't support fields with complex source."

        related_descriptor = get_attribute(self.Meta.model, nested_serializer.source_attrs)

        if isinstance(related_descriptor, related_descriptors.ReverseOneToOneDescriptor):
            return related_descriptor.related.field, 'forward'
        if isinstance(related_descriptor, related_descriptors.ReverseManyToOneDescriptor):
            return related_descriptor.field, 'forward'

        if (isinstance(related_descriptor, related_descriptors.ForwardManyToOneDescriptor) and
                isinstance(related_descriptor.field, related.OneToOneField)):
            return related_descriptor.field, 'reverse'

        assert False, "We doen't support many to many relation and forward many to one " \
                      "because updating this relation have side effect."

    def _get_related_data(self, instance, nested_serializer):
        """
        Return value of foreign key and additional fields on the basis of which relation
        between parent and nested serializers is formed.
        :param instance:
        :param nested_serializer:
        :return: Dictionary with fields values.
        """
        related_model_field, relation_type = self._get_related_model_field(nested_serializer)

        data = {
            lr_field.attname: getattr(instance, fr_field.attname)
            for lr_field, fr_field in related_model_field.related_fields
        }

        if isinstance(related_model_field, GenericRelation):
            data.update({
                related_model_field.content_type_field_name: ContentType.objects.get_for_model(instance),
            })
        if isinstance(related_model_field, CodedGenericRelation):
            data.update({
                related_model_field.code_field: related_model_field.code,
            })

        return data

    def _save_nested_data(self, instance, field, data):
        related_model_field, relation_type = self._get_related_model_field(field)

        if instance:
            try:
                nested_instance = field.get_attribute(instance)
            except (ObjectDoesNotExist, AttributeError):
                nested_instance = None
        else:
            nested_instance = None

        # Object forced set to null.
        if data is None:
            if nested_instance and relation_type == 'forward':
                nested_instance.delete()
            return None

        if relation_type == 'forward':
            assert instance, "In the case for forward relation between parent and child " \
                             "saving nested serializer require parent instance."
            related_data = self._get_related_data(instance, field)
            if getattr(field, 'many', False):
                data = [OrderedDict(d, **related_data) for d in data]
            else:
                data = OrderedDict(data, **related_data)

        if nested_instance:
            nested_instance = field.update(nested_instance, data)
        else:
            nested_instance = field.create(data)

        return nested_instance

    @method_decorator(transaction.atomic)
    def create(self, validated_data):
        # Separate nested data.
        nested_data, validated_data = pop_keys(validated_data, self.writable_nested_serializers)

        forward_nested_data = {}
        errors = {}
        for field_name, data in nested_data.items():
            field = self.fields[field_name]

            related_model_field, relation_type = self._get_related_model_field(field)
            if relation_type == 'forward':
                forward_nested_data[field_name] = data
                continue

            try:
                nested_instance = self._save_nested_data(None, field, data)
            except serializers.ValidationError as exc:
                errors[field_name] = exc.detail
            else:
                validated_data[field_name] = nested_instance

        if errors:
            raise serializers.ValidationError(errors)

        instance = super(WritableNestedParentSerializerMixin, self).create(validated_data)

        errors = dict()
        for field_name, data in forward_nested_data.items():
            field = self.fields[field_name]

            try:
                self._save_nested_data(instance, field, data)
            except serializers.ValidationError as exc:
                errors[field_name] = exc.detail

        if errors:
            raise serializers.ValidationError(errors)

        return instance

    @method_decorator(transaction.atomic)
    def update(self, instance, validated_data):
        # Separate nested data.
        nested_data, validated_data = pop_keys(validated_data, self.writable_nested_serializers)

        forward_nested_data = {}
        errors = {}
        for field_name, data in nested_data.items():
            field = self.fields[field_name]

            related_model_field, relation_type = self._get_related_model_field(field)
            if relation_type == 'forward':
                forward_nested_data[field_name] = data
                continue

            try:
                nested_instance = self._save_nested_data(instance, field, data)
            except serializers.ValidationError as exc:
                errors[field_name] = exc.detail
            else:
                validated_data[field_name] = nested_instance

        if errors:
            raise serializers.ValidationError(errors)

        instance = super(WritableNestedParentSerializerMixin, self).update(instance, validated_data)

        errors = dict()
        for field_name, data in forward_nested_data.items():
            field = self.fields[field_name]

            try:
                self._save_nested_data(instance, field, data)
            except serializers.ValidationError as exc:
                errors[field_name] = exc.detail

        if errors:
            raise serializers.ValidationError(errors)

        return instance


class WritableNestedSerializerMixin(DeletableSerializerMixin, WritableNestedChildSerializerMixin,
                                    WritableNestedParentSerializerMixin):
    class Meta(DeletableSerializerMixin.Meta, WritableNestedChildSerializerMixin.Meta):
        pass
