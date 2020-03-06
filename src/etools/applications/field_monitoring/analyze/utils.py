from typing import Optional, Union

from django.utils import timezone

from etools.applications.partners.models import Intervention, PartnerOrganization
from etools.applications.reports.models import Result


def get_days_since_last_visit(obj: Union[PartnerOrganization, Intervention, Result]) -> Optional[int]:
    if not hasattr(obj, 'last_visit'):
        raise RuntimeError('last_visit was not annotated')

    if not obj.last_visit:
        return None

    return (timezone.now().date() - obj.last_visit).days


def get_avg_days_between_visits(obj: Union[Intervention, Result]) -> Optional[int]:
    if not all([hasattr(obj, 'completed_visits'), hasattr(obj, 'last_visit'), hasattr(obj, 'first_visit')]):
        raise RuntimeError('some of the required fields are missing. please check annotates')

    if obj.completed_visits in [0, 1]:  # nothing to calculate
        return None

    if not obj.last_visit or not obj.first_visit:  # possible only for corrupted data; dates are required
        return None

    return int((obj.last_visit - obj.first_visit).days / (obj.completed_visits - 1))
