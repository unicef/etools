
from rest_framework import serializers
from rest_framework.fields import empty, Field, SkipField
from rest_framework.utils import model_meta
from rest_framework_recursive.fields import RecursiveField

from etools.applications.utils.common.utils import get_attribute_smart
from etools.applications.utils.writable_serializers.serializers import WritableListSerializer


class builtin_field:
    pass


class SeparatedReadWriteField(Field):
    read_field = None
    write_field = None

    def __init__(self, read_field, write_field=builtin_field, *args, **kwargs):
        super(SeparatedReadWriteField, self).__init__(*args, **kwargs)

        self.read_field = read_field
        self.write_field = write_field

        # update fields from kwargs
        for kwarg_name in {'label', } & set(kwargs.keys()):
            setattr(self.read_field, kwarg_name, kwargs[kwarg_name])

            if self.write_field is not builtin_field:
                setattr(self.write_field, kwarg_name, kwargs[kwarg_name])

    def to_representation(self, value):
        return self.read_field.to_representation(value)

    def to_internal_value(self, data):
        return self.write_field.to_internal_value(data)

    def get_validators(self):
        return self.write_field.get_validators()

    def validate_empty_values(self, data):
        """
        Validate empty values, and either:

        * Raise `ValidationError`, indicating invalid data.
        * Raise `SkipField`, indicating that the field should be ignored.
        * Return (True, data), indicating an empty value that should be
          returned without any further validation being applied.
        * Return (False, data), indicating a non-empty value, that should
          have validation applied as normal.
        """
        if data is empty:
            if getattr(self.root, 'partial', False):
                raise SkipField()
            if self.write_field.required:
                self.fail('required')
            return (True, self.get_default())

        if data is None:
            if not self.write_field.allow_null:
                self.fail('null')
            return (True, None)

        return (False, data)

    def _build_field(self):
        model = getattr(self.parent.Meta, 'model')
        depth = getattr(self.parent.Meta, 'depth', 0)
        info = model_meta.get_field_info(model)

        # Determine any extra field arguments and hidden fields that
        # should be included
        extra_kwargs = self.parent.get_extra_kwargs()
        extra_kwargs.update(self._kwargs)
        extra_kwargs, hidden_fields = self.parent.get_uniqueness_extra_kwargs(
            [self.field_name], [self], extra_kwargs
        )
        extra_field_kwargs = {
            key: value for key, value in self._kwargs.items()
            if key not in ['read_field']
        }

        # Determine the serializer field class and keyword arguments.
        field_class, field_kwargs = self.parent.build_field(
            self.field_name, info, model, depth
        )

        # Include any kwargs defined in `Meta.extra_kwargs`
        extra_field_kwargs.update(
            extra_kwargs.get(self.field_name, {})
        )
        field_kwargs = self.parent.include_extra_kwargs(
            field_kwargs, extra_field_kwargs
        )

        # Create the serializer field.
        return field_class(**field_kwargs)

    def bind(self, field_name, parent):
        super(SeparatedReadWriteField, self).bind(field_name, parent)

        self.read_field.bind(field_name, parent)

        if self.write_field is builtin_field:
            self.write_field = self._build_field()
        self.write_field.bind(field_name, parent)


class WriteListSerializeFriendlyRecursiveField(RecursiveField):
    @property
    def proxied(self):
        self._proxied = super(WriteListSerializeFriendlyRecursiveField, self).proxied
        if self._proxied and not self._proxied.context and self.bind_args[1] and self.bind_args[1].context:
            self._proxied.context = self.bind_args[1].context
        return self._proxied


class RecursiveListSerializer(WritableListSerializer):
    def update(self, instance, validated_data):
        if hasattr(self.child, 'proxied'):
            self.child = self.child.proxied
        return super(RecursiveListSerializer, self).update(instance, validated_data)


class CommaSeparatedExportField(serializers.Field):
    export_attr = None

    def __init__(self, *args, **kwargs):
        self.export_attr = kwargs.pop('export_attr', None)
        super(CommaSeparatedExportField, self).__init__(*args, **kwargs)

    def get_attribute(self, instance):
        try:
            return get_attribute_smart(instance, self.source_attrs)
        except (KeyError, AttributeError) as exc:
            if not self.required and self.default is empty:
                raise SkipField()
            msg = (
                'Got {exc_type} when attempting to get a value for field '
                '`{field}` on serializer `{serializer}`.\nThe serializer '
                'field might be named incorrectly and not match '
                'any attribute or key on the `{instance}` instance.\n'
                'Original exception text was: {exc}.'.format(
                    exc_type=type(exc).__name__,
                    field=self.field_name,
                    serializer=self.parent.__class__.__name__,
                    instance=instance.__class__.__name__,
                    exc=exc
                )
            )
            raise type(exc)(msg)

    def to_representation(self, value):
        value = set(value)

        if self.export_attr:
            value = [get_attribute_smart(item, self.export_attr) for item in value]

        return ', '.join([str(item) for item in value if item])


class DynamicChoicesField(serializers.ChoiceField):
    def __init__(self, *args, **kwargs):
        self._current_choices = {}
        super(DynamicChoicesField, self).__init__(*args, **kwargs)

    @property
    def choices(self):
        return self._current_choices

    @choices.setter
    def choices(self, value):
        self._current_choices = value

    @property
    def choice_strings_to_values(self):
        return {
            str(key): key for key in self.choices.keys()
        }

    @choice_strings_to_values.setter
    def choice_strings_to_values(self, value):
        # no need to do here anything
        return
