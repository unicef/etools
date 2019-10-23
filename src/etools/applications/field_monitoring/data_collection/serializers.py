from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework_bulk import BulkListSerializer, BulkSerializerMixin
from unicef_attachments.fields import FileTypeModelChoiceField
from unicef_attachments.models import FileType
from unicef_attachments.serializers import BaseAttachmentSerializer
from unicef_restlib.serializers import UserContextSerializerMixin

from etools.applications.field_monitoring.data_collection.models import ActivityQuestion, StartedChecklist, \
    ChecklistOverallFinding, Finding
from etools.applications.field_monitoring.fm_settings.serializers import QuestionListSerializer, OptionSerializer
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
    question = QuestionListSerializer()
    partner = MinimalPartnerOrganizationListSerializer()
    cp_output = MinimalOutputListSerializer()
    intervention = MinimalInterventionListSerializer()

    class Meta:
        model = ActivityQuestion
        list_serializer_class = BulkListSerializer
        fields = (
            'id', 'partner', 'cp_output', 'intervention',
            'question', 'specific_details', 'is_enabled'
        )
        read_only_fields = ('question', 'partner', 'cp_output', 'intervention',)


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


class FindingQuestionSerializer(serializers.ModelSerializer):
    answer_type = serializers.ReadOnlyField(source='question.answer_type')
    text = serializers.ReadOnlyField(source='question.text')
    options = OptionSerializer(source='question.options', many=True)

    class Meta:
        model = ActivityQuestion
        fields = ('answer_type', 'text', 'specific_details', 'options',)


class FindingSerializer(serializers.ModelSerializer):
    question = FindingQuestionSerializer(source='activity_question', read_only=True)

    class Meta:
        model = Finding
        fields = ('id', 'question', 'value',)
