from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers

from unicef_attachments.fields import FileTypeModelChoiceField
from unicef_attachments.models import FileType
from unicef_attachments.serializers import BaseAttachmentSerializer
from unicef_restlib.serializers import WritableNestedSerializerMixin

from etools.applications.action_points.serializers import CommentSerializer, HistorySerializer
from etools.applications.field_monitoring.planning.models import YearPlan


class YearPlanAttachmentSerializer(BaseAttachmentSerializer):
    file_type = FileTypeModelChoiceField(
        label=_('Document Type'), queryset=FileType.objects.filter(code=YearPlan.ATTACHMENTS_FILE_TYPE_CODE)
    )

    class Meta(BaseAttachmentSerializer.Meta):
        pass


class YearPlanSerializer(WritableNestedSerializerMixin, serializers.ModelSerializer):
    other_aspects = CommentSerializer(many=True, required=False)
    history = HistorySerializer(many=True, label=_('History'), read_only=True)

    class Meta(WritableNestedSerializerMixin.Meta):
        model = YearPlan
        fields = (
            'prioritization_criteria', 'methodology_notes', 'target_visits',
            'modalities', 'partner_engagement', 'other_aspects', 'history'
        )
