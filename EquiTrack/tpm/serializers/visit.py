from __future__ import absolute_import

import itertools
from copy import copy

from django.db import models
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from ..models import TPMVisit, TPMPermission, TPMActivity, TPMVisitReportRejectComment, TPMActionPoint, \
    TPMPartnerStaffMember
from .attachments import TPMAttachmentsSerializer, TPMReportSerializer, TPMReportAttachmentsSerializer
from .partner import TPMPartnerLightSerializer, TPMPartnerStaffMemberSerializer
from activities.serializers import ActivitySerializer
from attachments.models import Attachment
from partners.models import InterventionResultLink, PartnerOrganization
from partners.serializers.interventions_v2 import InterventionCreateUpdateSerializer
from utils.permissions.serializers import StatusPermissionsBasedSerializerMixin, \
    StatusPermissionsBasedRootSerializerMixin
from utils.common.serializers.fields import SeparatedReadWriteField
from utils.writable_serializers.serializers import WritableNestedSerializerMixin
from users.serializers import MinimalUserSerializer, OfficeSerializer
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


class PartnerOrganizationLightSerializer(serializers.ModelSerializer):
    class Meta:
        model = PartnerOrganization
        fields = [
            'id', 'name'
        ]


class TPMVisitReportRejectCommentSerializer(TPMPermissionsBasedSerializerMixin,
                                            WritableNestedSerializerMixin,
                                            serializers.ModelSerializer):
    class Meta(TPMPermissionsBasedSerializerMixin.Meta, WritableNestedSerializerMixin.Meta):
        model = TPMVisitReportRejectComment
        fields = ['id', 'rejected_at', 'reject_reason', ]


class TPMActionPointSerializer(TPMPermissionsBasedSerializerMixin,
                               WritableNestedSerializerMixin,
                               serializers.ModelSerializer):
    author = MinimalUserSerializer(read_only=True)

    person_responsible = SeparatedReadWriteField(
        read_field=MinimalUserSerializer(read_only=True),
        required=True
    )

    is_responsible = serializers.SerializerMethodField()

    def get_is_responsible(self, obj):
        return self.get_user() == obj.person_responsible

    class Meta(TPMPermissionsBasedSerializerMixin.Meta, WritableNestedSerializerMixin.Meta):
        model = TPMActionPoint
        fields = [
            'id', 'author', 'person_responsible', 'is_responsible',
            'due_date', 'status', 'description', 'comments',
        ]

    def create(self, validated_data):
        validated_data['author'] = self.get_user()
        return super(TPMActionPointSerializer, self).create(validated_data)


class TPMActivitySerializer(TPMPermissionsBasedSerializerMixin, WritableNestedSerializerMixin,
                            ActivitySerializer):
    implementing_partner = SeparatedReadWriteField(
        read_field=PartnerOrganizationLightSerializer(read_only=True),
    )
    partnership = SeparatedReadWriteField(
        read_field=InterventionCreateUpdateSerializer(read_only=True),
    )

    cp_output = SeparatedReadWriteField(
        read_field=ResultSerializer(read_only=True, label=_('CP Output')),
        required=False,
    )

    locations = SeparatedReadWriteField(
        read_field=LocationLightSerializer(many=True, read_only=True),
    )

    section = SeparatedReadWriteField(
        read_field=SectionSerializer(read_only=True),
        required=True,
    )

    attachments = TPMAttachmentsSerializer(many=True, required=False, label=_('Related Documents'))
    report_attachments = TPMReportSerializer(many=True, required=False, label=_('Reports by Activity'))

    pv_applicable = serializers.SerializerMethodField()

    class Meta(TPMPermissionsBasedSerializerMixin.Meta, WritableNestedSerializerMixin.Meta):
        model = TPMActivity
        fields = [
            'id', 'implementing_partner', 'partnership', 'cp_output', 'section',
            'date', 'locations', 'attachments', 'report_attachments', 'additional_information',
            'pv_applicable',
        ]
        extra_kwargs = {
            'id': {'label': _('Activity ID')},
            'date': {'required': True},
            'implementing_partner': {'required': True},
            'partnership': {'required': True, 'label': _('PD/SSFA')},
        }

    def get_pv_applicable(self, obj):
        return Attachment.objects.filter(
            models.Q(
                object_id=obj.tpm_visit_id,
                content_type__app_label=obj.tpm_visit._meta.app_label,
                content_type__model=obj.tpm_visit._meta.model_name,
                file_type__name='overall_report'
            ) | models.Q(
                object_id=obj.id,
                content_type__app_label=obj._meta.app_label,
                content_type__model=obj._meta.model_name,
                file_type__name='report'
            )
        ).exists()


class TPMVisitLightSerializer(StatusPermissionsBasedRootSerializerMixin, WritableNestedSerializerMixin,
                              serializers.ModelSerializer):
    tpm_partner = SeparatedReadWriteField(
        read_field=TPMPartnerLightSerializer(label=_('TPM Name'), read_only=True),
    )

    offices = SeparatedReadWriteField(
        read_field=OfficeSerializer(read_only=True, many=True, label=_('Office(s) of UNICEF Focal Point(s)')),
    )

    unicef_focal_points = SeparatedReadWriteField(
        read_field=MinimalUserSerializer(read_only=True, many=True, label=_('UNICEF Focal Points')),
    )

    tpm_partner_focal_points = SeparatedReadWriteField(
        read_field=TPMPartnerStaffMemberSerializer(read_only=True, many=True, label=_('TPM Focal Points')),
    )

    status_date = serializers.ReadOnlyField()

    implementing_partners = serializers.SerializerMethodField()
    locations = serializers.SerializerMethodField()
    sections = serializers.SerializerMethodField()

    def get_implementing_partners(self, obj):
        return PartnerOrganizationLightSerializer(
            set(map(
                lambda a: a.implementing_partner,
                obj.tpm_activities.all()
            )),
            many=True
        ).data

    def get_locations(self, obj):
        return LocationLightSerializer(
            set(itertools.chain(*map(
                lambda a: a.locations.all(),
                obj.tpm_activities.all()
            ))),
            many=True
        ).data

    def get_sections(self, obj):
        return SectionSerializer(
            set(map(
                lambda a: a.section,
                obj.tpm_activities.all()
            )),
            many=True
        ).data

    class Meta(StatusPermissionsBasedRootSerializerMixin.Meta, WritableNestedSerializerMixin.Meta):
        model = TPMVisit
        permission_class = TPMPermission
        fields = [
            'id', 'start_date', 'end_date', 'tpm_partner',
            'implementing_partners', 'locations', 'sections',
            'status', 'status_date', 'reference_number',
            'offices', 'tpm_partner_focal_points', 'unicef_focal_points',
            'date_created', 'date_of_assigned', 'date_of_tpm_accepted',
            'date_of_tpm_rejected', 'date_of_tpm_reported', 'date_of_unicef_approved',
            'date_of_tpm_report_rejected', 'date_of_cancelled',
        ]


class TPMVisitSerializer(TPMVisitLightSerializer):
    tpm_activities = TPMActivitySerializer(many=True, required=False)

    report_attachments = TPMReportAttachmentsSerializer(many=True, required=False, label=_('Overall Visit Reports'))

    report_reject_comments = TPMVisitReportRejectCommentSerializer(many=True, read_only=True)

    action_points = TPMActionPointSerializer(label=_('Activity information'), many=True, required=False)

    def validate(self, attrs):
        validated_data = super(TPMVisitSerializer, self).validate(attrs)

        tpm_partner = validated_data.get('tpm_partner', self.instance.tpm_partner if self.instance else None)

        if 'tpm_partner_focal_points' in validated_data:
            tpm_partner_focal_points = set(map(lambda x: x.id, validated_data['tpm_partner_focal_points']))
            diff = tpm_partner_focal_points - set(TPMPartnerStaffMember.objects.filter(
                id__in=tpm_partner_focal_points,
                tpm_partner_id=tpm_partner.id
            ).values_list('id', flat=True))

            if diff:
                raise ValidationError({
                    'tpm_partner_focal_points': [
                        self.fields['tpm_partner_focal_points'].write_field.child_relation
                            .error_messages['does_not_exist'].format(pk_value=pk)
                        for pk in diff
                    ]
                })

        return validated_data

    class Meta(TPMVisitLightSerializer.Meta):
        fields = TPMVisitLightSerializer.Meta.fields + [
            'tpm_activities', 'report_attachments', 'action_points',
            'reject_comment', 'approval_comment',
            'visit_information', 'report_reject_comments',
        ]
        extra_kwargs = {
            'tpm_activities': {'label': _('Activities Information')},
            'tpm_partner': {'required': True, 'label': _('TPM Name')},
            'unicef_focal_points': {'required': True},
        }


class TPMVisitDraftSerializer(TPMVisitSerializer):
    class Meta(TPMVisitSerializer.Meta):
        extra_kwargs = copy(TPMVisitSerializer.Meta.extra_kwargs)
        extra_kwargs['tpm_partner']['required'] = False
        extra_kwargs['unicef_focal_points']['required'] = False
