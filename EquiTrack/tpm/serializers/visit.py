from django.contrib.auth import get_user_model
from django.db import models
from rest_framework import serializers

from locations.models import Location
from locations.serializers import LocationLightSerializer
from partners.models import Intervention, InterventionResultLink
from partners.serializers.interventions_v2 import InterventionDetailSerializer
from reports.models import Sector
from reports.serializers.v1 import SectorLightSerializer
from tpm.models import TPMVisit, TPMLocation, TPMPartner, \
                       TPMPermission, TPMActivity, TPMSectorCovered, TPMLowResult
from tpm.serializers.attachments import TPMAttachmentsSerializer
from utils.permissions.serializers import StatusPermissionsBasedSerializerMixin, \
    StatusPermissionsBasedRootSerializerMixin
from utils.common.serializers.fields import SeparatedReadWriteField
from tpm.serializers.partner import TPMPartnerLightSerializer
from users.serializers import MinimalUserSerializer
from utils.writable_serializers.serializers import WritableNestedSerializerMixin


class TPMPermissionsBasedSerializerMixin(StatusPermissionsBasedSerializerMixin):
    class Meta(StatusPermissionsBasedSerializerMixin.Meta):
        permission_class = TPMPermission


class TPMLocationSerializer(TPMPermissionsBasedSerializerMixin, WritableNestedSerializerMixin,
                            serializers.ModelSerializer):
    location = SeparatedReadWriteField(
        read_field=LocationLightSerializer(read_only=True),
    )

    class Meta(TPMPermissionsBasedSerializerMixin.Meta, WritableNestedSerializerMixin.Meta):
        model = TPMLocation
        fields = ['id', 'location', 'start_date', 'end_date', 'type_of_site']


class TPMLowResultSerializer(TPMPermissionsBasedSerializerMixin, WritableNestedSerializerMixin,
                            serializers.ModelSerializer):
    tpm_locations = TPMLocationSerializer(many=True)

    class Meta(TPMPermissionsBasedSerializerMixin.Meta, WritableNestedSerializerMixin.Meta):
        model = TPMLowResult
        fields = ['id', 'result', 'tpm_locations']


class TPMSectorCoveredSerializer(TPMPermissionsBasedSerializerMixin, WritableNestedSerializerMixin,
                            serializers.ModelSerializer):
    tpm_low_results = TPMLowResultSerializer(many=True)
    sector = SeparatedReadWriteField(
        read_field=SectorLightSerializer(read_only=True),
    )

    class Meta(TPMPermissionsBasedSerializerMixin.Meta, WritableNestedSerializerMixin.Meta):
        model = TPMSectorCovered
        fields = ['id', 'sector', 'tpm_low_results']


class TPMActivitySerializer(TPMPermissionsBasedSerializerMixin, WritableNestedSerializerMixin,
                           serializers.ModelSerializer):
    tpm_sectors = TPMSectorCoveredSerializer(many=True)

    partnership = SeparatedReadWriteField(
        read_field=InterventionDetailSerializer(read_only=True),
    )

    unicef_focal_points = SeparatedReadWriteField(
        read_field=MinimalUserSerializer(read_only=True, many=True),
    )

    class Meta(TPMPermissionsBasedSerializerMixin.Meta, WritableNestedSerializerMixin.Meta):
        model = TPMActivity
        fields = ['id', 'partnership', 'tpm_sectors', 'unicef_focal_points']


class InterventionResultLinkVisitSerializer(serializers.ModelSerializer):
    name = serializers.ReadOnlyField(source="cp_output.name")

    class Meta:
        model = InterventionResultLink
        fields = [
            'id', 'name'
        ]


class TPMVisitLightSerializer(StatusPermissionsBasedRootSerializerMixin, WritableNestedSerializerMixin,
                              serializers.ModelSerializer):
    tpm_activities = TPMActivitySerializer(many=True)

    tpm_partner = SeparatedReadWriteField(
        read_field=TPMPartnerLightSerializer(read_only=True),
    )

    class Meta(StatusPermissionsBasedRootSerializerMixin.Meta, WritableNestedSerializerMixin.Meta):
        model = TPMVisit
        permission_class = TPMPermission
        fields = [
            'id', 'start_date', 'end_date',
            'tpm_activities', 'tpm_partner',
            'status', 'reference_number',
        ]


class TPMVisitSerializer(TPMVisitLightSerializer):
    attachments = TPMAttachmentsSerializer(read_only=True, many=True)

    class Meta(TPMVisitLightSerializer.Meta):
        fields = TPMVisitLightSerializer.Meta.fields + [
            'reject_comment',
            'attachments',
        ]
