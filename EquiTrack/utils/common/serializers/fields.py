from rest_framework.fields import Field
from rest_framework.utils import model_meta
from rest_framework_recursive.fields import RecursiveField

from utils.writable_serializers.serializers import WritableListSerializer


class builtin_field:
    pass


class SeparatedReadWriteField(Field):
    read_field = None
    write_field = None

    def __init__(self, read_field, write_field=builtin_field, *args, **kwargs):
        super(SeparatedReadWriteField, self).__init__(*args, **kwargs)

        self.read_field = read_field
        self.write_field = write_field

    def to_representation(self, value):
        return self.read_field.to_representation(value)

    def to_internal_value(self, data):
        return self.write_field.to_internal_value(data)

    def get_validators(self):
        return self.write_field.get_validators()

    def _build_field(self):
        model = getattr(self.parent.Meta, 'model')
        depth = getattr(self.parent.Meta, 'depth', 0)
        info = model_meta.get_field_info(model)

        # Determine any extra field arguments and hidden fields that
        # should be included
        extra_kwargs = self.parent.get_extra_kwargs()
        extra_kwargs, hidden_fields = self.parent.get_uniqueness_extra_kwargs(
            [self.field_name], [self], extra_kwargs
        )

        # Determine the serializer field class and keyword arguments.
        field_class, field_kwargs = self.parent.build_field(
            self.field_name, info, model, depth
        )

        # Include any kwargs defined in `Meta.extra_kwargs`
        extra_field_kwargs = extra_kwargs.get(self.field_name, {})
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
