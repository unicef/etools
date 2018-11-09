from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from unicef_locations.serializers import LocationSerializer

from etools.applications.field_monitoring.settings.models import LocationSite


class LocationSiteSerializer(serializers.ModelSerializer):
    parent = LocationSerializer(read_only=True)
    is_active = serializers.ChoiceField(choices=(
        (True, _('Active')),
        (False, _('Inactive')),
    ), label=_('Status'), required=False)

    class Meta:
        model = LocationSite
        fields = ['id', 'name', 'p_code', 'parent', 'point', 'security_detail', 'is_active']
        extra_kwargs = {
            'point': {'required': True},
        }
