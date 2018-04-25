
import itertools

from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from etools.applications.activities.serializers import ActivitySerializer
from etools.applications.locations.serializers import LocationLightSerializer
from etools.applications.partners.models import InterventionResultLink, PartnerType
from etools.applications.partners.serializers.interventions_v2 import InterventionCreateUpdateSerializer
from etools.applications.partners.serializers.partner_organization_v2 import MinimalPartnerOrganizationListSerializer
from etools.applications.reports.serializers.v1 import ResultSerializer, SectorSerializer
from etools.applications.tpm.models import (TPMActionPoint, TPMActivity, TPMPermission,
                                            TPMVisit, TPMVisitReportRejectComment,)
from etools.applications.tpm.serializers.attachments import (TPMAttachmentsSerializer,
                                                             TPMReportAttachmentsSerializer, TPMReportSerializer,)
from etools.applications.tpm.serializers.partner import TPMPartnerLightSerializer, TPMPartnerStaffMemberSerializer
from etools.applications.tpm.tpmpartners.models import TPMPartnerStaffMember
from etools.applications.users.serializers import MinimalUserSerializer, OfficeSerializer
from etools.applications.utils.common.serializers.fields import SeparatedReadWriteField
from etools.applications.utils.permissions.serializers import (StatusPermissionsBasedRootSerializerMixin,
                                                               StatusPermissionsBasedSerializerMixin,)
from etools.applications.utils.writable_serializers.serializers import WritableNestedSerializerMixin


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


class TPMActionPointSerializer(TPMPermissionsBasedSerializerMixin,
                               WritableNestedSerializerMixin,
                               serializers.ModelSerializer):
    author = MinimalUserSerializer(read_only=True, label=_('Assigned By'))

    person_responsible = SeparatedReadWriteField(
        read_field=MinimalUserSerializer(read_only=True, label=_('Person Responsible')),
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
    partner = SeparatedReadWriteField(
        read_field=MinimalPartnerOrganizationListSerializer(read_only=True, label=_('Implementing Partner')),
    )
    intervention = SeparatedReadWriteField(
        read_field=InterventionCreateUpdateSerializer(read_only=True, label=_('PD/SSFA')),
        required=False,
    )

    cp_output = SeparatedReadWriteField(
        read_field=ResultSerializer(read_only=True, label=_('CP Output')),
        required=False,
    )

    locations = SeparatedReadWriteField(
        read_field=LocationLightSerializer(many=True, read_only=True, label=_('Locations')),
    )

    section = SeparatedReadWriteField(
        read_field=SectorSerializer(read_only=True, label=_('Section')),
        required=True,
    )

    attachments = TPMAttachmentsSerializer(many=True, required=False, label=_('Related Documents'))
    report_attachments = TPMReportSerializer(many=True, required=False, label=_('Reports by Activity'))

    pv_applicable = serializers.BooleanField(read_only=True)

    def _validate_partner_intervention(self, validated_data, instance=None):
        if 'partner' in validated_data and 'intervention' not in validated_data:
            validated_data['intervention'] = None

        partner = validated_data.get('partner', instance.partner if instance else None)
        intervention = validated_data.get('intervention', instance.intervention if instance else None)

        if partner and partner.partner_type not in [PartnerType.GOVERNMENT, PartnerType.BILATERAL_MULTILATERAL] \
                and not intervention:
            raise ValidationError({'intervention': _('This field is required.')})

        return instance

    def create(self, validated_data):
        self._validate_partner_intervention(validated_data)
        return super(TPMActivitySerializer, self).create(validated_data)

    def update(self, instance, validated_data):
        self._validate_partner_intervention(validated_data, instance=instance)
        return super(TPMActivitySerializer, self).update(instance, validated_data)

    class Meta(TPMPermissionsBasedSerializerMixin.Meta, WritableNestedSerializerMixin.Meta):
        model = TPMActivity
        fields = [
            'id', 'partner', 'intervention', 'cp_output', 'section',
            'date', 'locations', 'attachments', 'report_attachments', 'additional_information',
            'pv_applicable',
        ]
        extra_kwargs = {
            'id': {'label': _('Activity ID')},
            'date': {'required': True},
            'partner': {'required': True},
        }


class TPMVisitLightSerializer(StatusPermissionsBasedRootSerializerMixin, WritableNestedSerializerMixin,
                              serializers.ModelSerializer):
    tpm_partner = SeparatedReadWriteField(
        read_field=TPMPartnerLightSerializer(label=_('TPM Partner'), read_only=True),
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

    status_date = serializers.ReadOnlyField(label=_('Status Date'))

    implementing_partners = serializers.SerializerMethodField(label=_('Implementing Partners'))
    locations = serializers.SerializerMethodField(label=_('Locations'))
    sections = serializers.SerializerMethodField(label=_('Sections'))

    def get_implementing_partners(self, obj):
        return MinimalPartnerOrganizationListSerializer(
            set(map(
                lambda a: a.partner,
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
        return SectorSerializer(
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
        extra_kwargs = {
            'reference_number': {
                'label': _('Reference Number'),
            },
        }


class TPMVisitSerializer(TPMVisitLightSerializer):
    tpm_activities = TPMActivitySerializer(many=True, required=False, label=_('Site Visit Schedule'))

    report_attachments = TPMReportAttachmentsSerializer(many=True, required=False, label=_('Overall Visit Reports'))

    report_reject_comments = TPMVisitReportRejectCommentSerializer(many=True, read_only=True)

    action_points = TPMActionPointSerializer(label=_('Activity Information'), many=True, required=False)

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
            'tpm_partner': {'required': True},
            'unicef_focal_points': {'required': True},
            'tpm_partner_focal_points': {'required': True},
        }


class TPMVisitDraftSerializer(TPMVisitSerializer):
    class Meta(TPMVisitSerializer.Meta):
        extra_kwargs = {}
