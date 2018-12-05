from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from etools.applications.field_monitoring.fm_settings.models import FMMethodType
from etools.applications.field_monitoring.shared.models import FMMethod
from etools.applications.permissions_simplified.serializers import SafeReadOnlySerializerMixin


class FMMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = FMMethod
        fields = ('id', 'name', 'is_types_applicable')


class FMMethodTypeSerializer(SafeReadOnlySerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = FMMethodType
        fields = ('id', 'method', 'name')
        extra_kwargs = {
            'name': {'label': _('Recommended Type')}
        }

    def validate_method(self, method):
        if not method:
            self.fail('required')
        elif not method.is_types_applicable:
            raise ValidationError(_('Unable to add type for this Method'))

        return method
