"""
Shared helpers for resolving dynamic option types (e.g. epd_activities) to value/label pairs.
Used by the data-collection blueprint and by the findings API serializers.
"""
from typing import List, Tuple

from etools.applications.reports.models import InterventionActivity


def get_dynamic_options_pairs(
    dynamic_options_type: str, level: str, target
) -> List[Tuple[str, str]]:
    """
    Return list of (value, label) for the given dynamic_options_type and target.
    """
    if dynamic_options_type == 'epd_activities' and level == 'intervention':
        qs = (
            InterventionActivity.objects.filter(
                result__result_link__intervention_id=target.id,
            )
            .distinct()
            .order_by('code', 'name', 'id')
        )

        def _label(obj):
            if obj.code:
                return f'{obj.code} - {obj.name}'
            return obj.name

        return [(str(obj.id), _label(obj)) for obj in qs]
    return []
