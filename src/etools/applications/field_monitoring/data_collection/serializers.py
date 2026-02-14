import itertools

from django.utils.translation import gettext as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from unicef_attachments.fields import FileTypeModelChoiceField
from unicef_attachments.models import FileType
from unicef_attachments.serializers import BaseAttachmentSerializer
from unicef_restlib.serializers import UserContextSerializerMixin

from etools.applications.field_monitoring.data_collection.models import (
    ActivityOverallFinding,
    ActivityQuestion,
    ActivityQuestionOverallFinding,
    ChecklistOverallFinding,
    Finding,
    StartedChecklist,
)
from etools.applications.field_monitoring.fm_settings.serializers import (
    FMCommonAttachmentSerializer,
    QuestionSerializer,
)
from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.partners.serializers.interventions_v2 import MinimalInterventionListSerializer
from etools.applications.partners.serializers.partner_organization_v2 import MinimalPartnerOrganizationListSerializer
from etools.applications.reports.serializers.v2 import MinimalOutputListSerializer
from etools.applications.users.serializers import MinimalUserSerializer


class ActivityDataCollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonitoringActivity
        fields = ('id',)


class ActivityQuestionSerializer(serializers.ModelSerializer):
    partner = MinimalPartnerOrganizationListSerializer(read_only=True)
    cp_output = MinimalOutputListSerializer(read_only=True)
    intervention = MinimalInterventionListSerializer(read_only=True)

    question = QuestionSerializer(read_only=True)

    class Meta:
        model = ActivityQuestion
        fields = (
            'id', 'question',
            'text', 'is_hact',
            'is_enabled', 'specific_details',
            'partner', 'intervention', 'cp_output',
        )


class ActivityQuestionFindingSerializer(serializers.ModelSerializer):
    author = MinimalUserSerializer(read_only=True, source='started_checklist.author')

    class Meta:
        model = Finding
        fields = ('id', 'value', 'author')


class CompletedActivityQuestionFindingSerializer(ActivityQuestionFindingSerializer):
    checklist = serializers.ReadOnlyField(source='started_checklist.id')
    method = serializers.ReadOnlyField(source='started_checklist.method_id')

    class Meta(ActivityQuestionFindingSerializer.Meta):
        fields = ActivityQuestionFindingSerializer.Meta.fields + ('checklist', 'method',)


class CompletedActivityQuestionSerializer(ActivityQuestionSerializer):
    findings = CompletedActivityQuestionFindingSerializer(many=True, read_only=True, source='completed_findings')

    class Meta(ActivityQuestionSerializer.Meta):
        fields = ActivityQuestionSerializer.Meta.fields + ('findings',)


class ActivityReportAttachmentSerializer(BaseAttachmentSerializer):
    file_type = FileTypeModelChoiceField(
        label=_('Document Type'), queryset=FileType.objects.filter(code='fm_common')
    )

    class Meta(BaseAttachmentSerializer.Meta):
        pass

    def create(self, validated_data):
        validated_data['code'] = 'report_attachments'
        return super().create(validated_data)


class ChecklistSerializer(UserContextSerializerMixin, serializers.ModelSerializer):
    author = MinimalUserSerializer(read_only=True)

    class Meta:
        model = StartedChecklist
        fields = ('id', 'method', 'information_source', 'author',)

    def validate(self, attrs):
        validated_data = super().validate(attrs)

        method = validated_data.get('method', self.instance.method if self.instance else None)
        if method and method.use_information_source and not validated_data.get('information_source'):
            raise ValidationError({'information_source': [_('Information source is required')]}, code='required')

        return validated_data

    def create(self, validated_data):
        validated_data['author'] = self.get_user()
        return super().create(validated_data)


class ChecklistOverallFindingSerializer(serializers.ModelSerializer):
    attachments = BaseAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = ChecklistOverallFinding
        fields = ('id', 'partner', 'cp_output', 'intervention', 'narrative_finding_raw', 'attachments')
        read_only_fields = ('partner', 'cp_output', 'intervention')


class FindingSerializer(serializers.ModelSerializer):
    activity_question = ActivityQuestionSerializer(read_only=True)

    class Meta:
        model = Finding
        fields = ('id', 'activity_question', 'value',)


class CompletedChecklistOverallFindingSerializer(serializers.ModelSerializer):
    author = MinimalUserSerializer(read_only=True, source='started_checklist.author')
    checklist = serializers.ReadOnlyField(source='started_checklist.id')
    method = serializers.ReadOnlyField(source='started_checklist.method_id')
    information_source = serializers.ReadOnlyField(source='started_checklist.information_source')

    class Meta:
        model = ChecklistOverallFinding
        fields = ('author', 'method', 'checklist', 'information_source', 'narrative_finding_raw')


class ActivityOverallFindingSerializer(serializers.ModelSerializer):
    attachments = serializers.SerializerMethodField()
    findings = serializers.SerializerMethodField()

    class Meta:
        model = ActivityOverallFinding
        fields = (
            'id', 'partner', 'cp_output', 'intervention',
            'narrative_finding_raw', 'on_track',
            'attachments', 'findings'
        )
        read_only_fields = ('partner', 'cp_output', 'intervention')

    def _get_checklist_overall_findings(self, obj):
        return [
            finding
            for finding in itertools.chain(*(
                c.overall_findings.all()
                for c in obj.monitoring_activity.checklists.all()
            ))
            if (
                finding.partner_id == obj.partner_id and
                finding.cp_output_id == obj.cp_output_id and
                finding.intervention_id == obj.intervention_id
            )
        ]

    def get_attachments(self, obj):
        # attachments are contained in checklists overall findings, so need to extract them through the relations
        attachments = itertools.chain(*(
            finding.attachments.all() for finding in self._get_checklist_overall_findings(obj)
        ))
        return BaseAttachmentSerializer(instance=attachments, many=True).data

    def get_findings(self, obj):
        findings = self._get_checklist_overall_findings(obj)
        return CompletedChecklistOverallFindingSerializer(instance=findings, many=True).data


class ActivityQuestionOverallFindingSerializer(serializers.ModelSerializer):
    activity_question = CompletedActivityQuestionSerializer(read_only=True)

    class Meta:
        model = ActivityQuestionOverallFinding
        fields = ('id', 'activity_question', 'value',)


class ChecklistAttachmentSerializer(FMCommonAttachmentSerializer):
    checklist = ChecklistSerializer(read_only=True, source='content_object.started_checklist')
    partner = MinimalPartnerOrganizationListSerializer(read_only=True, source='content_object.partner')
    cp_output = MinimalOutputListSerializer(read_only=True, source='content_object.cp_output')
    intervention = MinimalInterventionListSerializer(read_only=True, source='content_object.intervention')

    class Meta(FMCommonAttachmentSerializer.Meta):
        fields = FMCommonAttachmentSerializer.Meta.fields + [
            'checklist', 'partner', 'cp_output', 'intervention',
        ]
