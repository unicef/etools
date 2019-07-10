from django.utils.translation import ugettext_lazy as _

from unicef_snapshot.serializers import SnapshotModelSerializer

from etools.applications.action_points.serializers import HistorySerializer
from etools.applications.field_monitoring.planning.models import YearPlan
from etools.applications.permissions_simplified.serializers import SafeReadOnlySerializerMixin


class YearPlanSerializer(SafeReadOnlySerializerMixin, SnapshotModelSerializer):
    history = HistorySerializer(many=True, label=_('History'), read_only=True)

    class Meta:
        model = YearPlan
        fields = (
            'prioritization_criteria', 'methodology_notes', 'target_visits',
            'modalities', 'partner_engagement', 'other_aspects', 'history',
        )
