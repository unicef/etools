import itertools

from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework_bulk import BulkListSerializer, BulkSerializerMixin
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
from etools.applications.field_monitoring.fm_settings.serializers import QuestionSerializer
from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.partners.serializers.interventions_v2 import MinimalInterventionListSerializer
from etools.applications.partners.serializers.partner_organization_v2 import MinimalPartnerOrganizationListSerializer
from etools.applications.reports.serializers.v2 import MinimalOutputListSerializer
from etools.applications.users.serializers import MinimalUserSerializer


class ActivityDataCollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonitoringActivity
        fields = ('id',)


class ActivityQuestionSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    partner = MinimalPartnerOrganizationListSerializer(read_only=True)
    cp_output = MinimalOutputListSerializer(read_only=True)
    intervention = MinimalInterventionListSerializer(read_only=True)

    question = QuestionSerializer(read_only=True)

    class Meta:
        model = ActivityQuestion
        list_serializer_class = BulkListSerializer
        fields = (
            'id', 'question', 'is_enabled',
            'partner', 'intervention', 'cp_output',
        )


class ActivityQuestionFindingSerializer(serializers.ModelSerializer):
    author = MinimalUserSerializer(read_only=True, source='started_checklist.author')

    class Meta:
        model = Finding
        fields = ('id', 'value', 'author')


class CompletedActivityQuestionSerializer(ActivityQuestionSerializer):
    findings = ActivityQuestionFindingSerializer(many=True, read_only=True, source='completed_findings')

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

    def create(self, validated_data):
        validated_data['author'] = self.get_user()
        return super().create(validated_data)


class ChecklistOverallFindingSerializer(serializers.ModelSerializer):
    attachments = BaseAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = ChecklistOverallFinding
        fields = ('id', 'partner', 'cp_output', 'intervention', 'narrative_finding', 'attachments')
        read_only_fields = ('partner', 'cp_output', 'intervention')


class FindingSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    activity_question = ActivityQuestionSerializer(read_only=True)

    class Meta:
        model = Finding
        list_serializer_class = BulkListSerializer
        fields = ('id', 'activity_question', 'value',)


class ActivityOverallFindingSerializer(serializers.ModelSerializer):
    attachments = serializers.SerializerMethodField()

    class Meta:
        model = ActivityOverallFinding
        fields = ('id', 'partner', 'cp_output', 'intervention', 'narrative_finding', 'on_track', 'attachments')
        read_only_fields = ('partner', 'cp_output', 'intervention')

    def get_attachments(self, obj):
        # attachments are contained in checklists overall findings, so need to extract them through the relations
        attachments = itertools.chain(*(
            finding.attachments.all() for finding in
            filter(
                lambda finding:
                    finding.partner_id == obj.partner_id and
                    finding.cp_output_id == obj.cp_output_id and
                    finding.intervention_id == obj.intervention_id,
                itertools.chain(*(
                    c.overall_findings.all()
                    for c in obj.monitoring_activity.checklists.all()
                ))
            )
        ))
        return BaseAttachmentSerializer(instance=attachments, many=True).data


class ActivityQuestionOverallFindingSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    activity_question = CompletedActivityQuestionSerializer(read_only=True)

    class Meta:
        model = ActivityQuestionOverallFinding
        list_serializer_class = BulkListSerializer
        fields = ('id', 'activity_question', 'value',)


class ChecklistAttachmentSerializer(BaseAttachmentSerializer):
    checklist = ChecklistSerializer(read_only=True, source='content_object.started_checklist')
    partner = MinimalPartnerOrganizationListSerializer(read_only=True, source='content_object.partner')
    cp_output = MinimalOutputListSerializer(read_only=True, source='content_object.cp_output')
    intervention = MinimalInterventionListSerializer(read_only=True, source='content_object.intervention')

    class Meta(BaseAttachmentSerializer.Meta):
        fields = BaseAttachmentSerializer.Meta.fields + [
            'checklist', 'partner', 'cp_output', 'intervention',
        ]
