from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Sum
from django.db.models.expressions import RawSQL
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from unicef_attachments.fields import FileTypeModelChoiceField
from unicef_attachments.models import FileType
from unicef_attachments.serializers import BaseAttachmentSerializer
from unicef_locations.serializers import LocationLightSerializer
from unicef_restlib.fields import SeparatedReadWriteField
from unicef_restlib.serializers import WritableNestedSerializerMixin
from unicef_snapshot.serializers import SnapshotModelSerializer

from etools.applications.action_points.serializers import CommentSerializer, HistorySerializer
from etools.applications.field_monitoring.planning.models import YearPlan, Task
from etools.applications.field_monitoring.settings.serializers.cp_outputs import CPOutputConfigDetailSerializer
from etools.applications.field_monitoring.settings.serializers.locations import LocationSiteLightSerializer
from etools.applications.partners.serializers.partner_organization_v2 import MinimalPartnerOrganizationListSerializer


class YearPlanAttachmentSerializer(BaseAttachmentSerializer):
    file_type = FileTypeModelChoiceField(
        label=_('Document Type'), queryset=FileType.objects.filter(code=YearPlan.ATTACHMENTS_FILE_TYPE_CODE)
    )

    class Meta(BaseAttachmentSerializer.Meta):
        pass


class YearPlanSerializer(WritableNestedSerializerMixin, SnapshotModelSerializer):
    other_aspects = CommentSerializer(many=True, required=False)
    history = HistorySerializer(many=True, label=_('History'), read_only=True)
    tasks_by_month = serializers.SerializerMethodField(label=_('Number Of Tasks By Month'))

    class Meta(WritableNestedSerializerMixin.Meta):
        model = YearPlan
        fields = (
            'prioritization_criteria', 'methodology_notes', 'target_visits',
            'modalities', 'partner_engagement', 'other_aspects', 'history',
            'tasks_by_month',
        )

    def get_tasks_by_month(self, obj):
        aggregates = {
            'p_{}'.format(i): Sum(RawSQL('plan_by_month[%s]', [i]))
            for i in range(1, 13)
        }
        return list(obj.tasks.aggregate(**aggregates).values())


class TaskListSerializer(serializers.ModelSerializer):
    cp_output_config = SeparatedReadWriteField(read_field=CPOutputConfigDetailSerializer())
    partner = SeparatedReadWriteField(read_field=MinimalPartnerOrganizationListSerializer())
    location = SeparatedReadWriteField(read_field=LocationLightSerializer())
    location_site = SeparatedReadWriteField(read_field=LocationSiteLightSerializer())

    class Meta:
        model = Task
        fields = (
            'id', 'cp_output_config', 'partner', 'intervention', 'location', 'location_site', 'plan_by_month'
        )

    def validate_plan_by_month(self, plan):
        try:
            self.Meta.model.clean_plan_by_month(plan)
        except DjangoValidationError as ex:
            raise ValidationError(ex.message)

        return plan


class TaskSerializer(TaskListSerializer):
    class Meta(TaskListSerializer.Meta):
        pass
