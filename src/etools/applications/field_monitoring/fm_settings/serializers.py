import json

from django.contrib.gis.db.models import Collect
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from unicef_attachments.fields import FileTypeModelChoiceField
from unicef_attachments.models import FileType
from unicef_attachments.serializers import BaseAttachmentSerializer
from unicef_locations.serializers import LocationLightSerializer, LocationSerializer

from etools.applications.field_monitoring.fm_settings.models import LocationSite, Method
from etools.applications.permissions_simplified.serializers import SafeReadOnlySerializerMixin
from etools.applications.reports.serializers.v2 import OutputListSerializer


class MethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Method
        fields = ('id', 'name')


class LocationSiteLightSerializer(SafeReadOnlySerializerMixin, serializers.ModelSerializer):
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


class LocationSiteSerializer(LocationSiteLightSerializer):
    parent = LocationSerializer(read_only=True)

    class Meta(LocationSiteLightSerializer.Meta):
        pass


class LocationFullSerializer(LocationLightSerializer):
    point = serializers.SerializerMethodField()
    geom = serializers.SerializerMethodField()
    is_leaf = serializers.BooleanField(source='is_leaf_node', read_only=True)

    class Meta(LocationLightSerializer.Meta):
        fields = LocationLightSerializer.Meta.fields + ('point', 'geom', 'is_leaf')

    def get_geom(self, obj):
        return json.loads(obj.geom.json) if obj.geom else {}

    def get_point(self, obj):
        point = obj.point or self.Meta.model.objects.aggregate(boundary=Collect('point'))['boundary'].centroid
        return json.loads(point.json)


class FieldMonitoringGeneralAttachmentSerializer(SafeReadOnlySerializerMixin, BaseAttachmentSerializer):
    file_type = FileTypeModelChoiceField(
        label=_('Document Type'), queryset=FileType.objects.filter(code='fm_common')
    )

    class Meta(BaseAttachmentSerializer.Meta):
        pass


class ResultSerializer(OutputListSerializer):
    name = serializers.ReadOnlyField()

    class Meta(OutputListSerializer.Meta):
        pass
