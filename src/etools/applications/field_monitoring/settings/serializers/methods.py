from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from etools.applications.field_monitoring.settings.models import MethodType
from etools.applications.field_monitoring.shared.models import Method
from etools.applications.permissions2.serializers import PermissionsBasedSerializerMixin


class MethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Method
        fields = ('id', 'name', 'is_types_applicable')


class MethodTypeSerializer(PermissionsBasedSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = MethodType
        fields = ('id', 'method', 'name')
        extra_kwargs = {
            'name': {'label': _('Recommended Type')}
        }

    def validate_method(self, method):
        if not method:
            self.fail('required')

        try:
            self.Meta.model.clean_method(method)
        except DjangoValidationError as ex:
            raise ValidationError(ex.message)

        return method
