from rest_framework import serializers

from audit.serializers.engagement import PartnerOrganizationLightSerializer
from partners.models import InterventionResultLink
from partners.serializers.interventions_v2 import InterventionCreateUpdateSerializer, InterventionListSerializer
from tpm.models import TPMVisit, TPMPermission, TPMActivity, TPMVisitReportRejectComment
from tpm.serializers.attachments import TPMAttachmentsSerializer, TPMReportAttachmentsSerializer
from utils.permissions.serializers import StatusPermissionsBasedSerializerMixin, \
    StatusPermissionsBasedRootSerializerMixin
from utils.common.serializers.fields import SeparatedReadWriteField
from tpm.serializers.partner import TPMPartnerLightSerializer, TPMPartnerStaffMemberSerializer
from users.serializers import MinimalUserSerializer, OfficeSerializer
from utils.writable_serializers.serializers import WritableNestedSerializerMixin
from users.serializers import SectionSerializer
from locations.serializers import LocationLightSerializer
from reports.serializers.v1 import ResultSerializer


class TPMPermissionsBasedSerializerMixin(StatusPermissionsBasedSerializerMixin):
    class Meta(StatusPermissionsBasedSerializerMixin.Meta):
        permission_class = TPMPermission


class InterventionResultLinkVisitSerializer(serializers.ModelSerializer):
    name = serializers.ReadOnlyField(source="cp_output.name")

    class Meta:
        model = InterventionResultLink
        fields = [
            'id', 'name'
        ]


class TPMVisitReportRejectCommentSerializer(TPMPermissionsBasedSerializerMixin,
                                            WritableNestedSerializerMixin,
                                            serializers.ModelSerializer):
    class Meta(TPMPermissionsBasedSerializerMixin.Meta, WritableNestedSerializerMixin.Meta):
        model = TPMVisitReportRejectComment
        fields = ['id', 'rejected_at', 'reject_reason', ]


class TPMActivityLightSerializer(TPMPermissionsBasedSerializerMixin, WritableNestedSerializerMixin,
                                 serializers.ModelSerializer):
    implementing_partner = SeparatedReadWriteField(
        read_field=PartnerOrganizationLightSerializer(read_only=True),
    )

    partnership = SeparatedReadWriteField(
        read_field=InterventionListSerializer(read_only=True),
    )

    cp_output = SeparatedReadWriteField(
        read_field=ResultSerializer(read_only=True),
        required=False,
    )

    locations = SeparatedReadWriteField(
        read_field=LocationLightSerializer(many=True, read_only=True),
    )

    class Meta(TPMPermissionsBasedSerializerMixin.Meta, WritableNestedSerializerMixin.Meta):
        model = TPMActivity
        fields = ['id', 'implementing_partner', 'partnership', 'cp_output', 'date', 'locations', ]


class TPMActivitySerializer(TPMActivityLightSerializer):
    partnership = SeparatedReadWriteField(
        read_field=InterventionCreateUpdateSerializer(read_only=True),
    )

    class Meta(TPMActivityLightSerializer.Meta):
        pass


class TPMVisitLightSerializer(StatusPermissionsBasedRootSerializerMixin, WritableNestedSerializerMixin,
                              serializers.ModelSerializer):
    tpm_activities = TPMActivityLightSerializer(many=True, required=False)

    tpm_partner = SeparatedReadWriteField(
        read_field=TPMPartnerLightSerializer(read_only=True),
    )

    sections = SeparatedReadWriteField(
        read_field=SectionSerializer(read_only=True, many=True),
    )

    offices = SeparatedReadWriteField(
        read_field=OfficeSerializer(read_only=True, many=True)
    )

    unicef_focal_points = SeparatedReadWriteField(
        read_field=MinimalUserSerializer(read_only=True, many=True),
    )

    tpm_partner_focal_points = SeparatedReadWriteField(
        read_field=TPMPartnerStaffMemberSerializer(read_only=True, many=True),
    )

    status_date = serializers.ReadOnlyField()

    class Meta(StatusPermissionsBasedRootSerializerMixin.Meta, WritableNestedSerializerMixin.Meta):
        model = TPMVisit
        permission_class = TPMPermission
        fields = [
            'id', 'start_date', 'end_date',
            'tpm_activities', 'tpm_partner',
            'status', 'status_date', 'reference_number',
            'sections', 'offices', 'tpm_partner_focal_points', 'unicef_focal_points',
            'date_created', 'date_of_assigned', 'date_of_tpm_accepted',
            'date_of_tpm_rejected', 'date_of_tpm_reported', 'date_of_unicef_approved',
            'date_of_tpm_report_rejected', 'date_of_cancelled',
        ]


class TPMVisitSerializer(TPMVisitLightSerializer):
    tpm_activities = TPMActivitySerializer(many=True, required=False)

    attachments = TPMAttachmentsSerializer(many=True, required=False)
    report = TPMReportAttachmentsSerializer(many=True, required=False)

    report_reject_comments = SeparatedReadWriteField(
        read_field=TPMVisitReportRejectCommentSerializer(many=True, read_only=True),
    )

    class Meta(TPMVisitLightSerializer.Meta):
        fields = TPMVisitLightSerializer.Meta.fields + [
            'reject_comment',
            'attachments',
            'report',
            'report_reject_comments',
        ]
        extra_kwargs = {
            'tpm_partner': {'required': True},
            'unicef_focal_points': {'required': True},
        }


class TPMVisitDraftSerializer(TPMVisitSerializer):
    class Meta(TPMVisitSerializer.Meta):
        extra_kwargs = {
            'tpm_partner': {'required': False},
        }
