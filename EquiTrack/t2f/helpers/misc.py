from __future__ import unicode_literals

from t2f.models import Travel


def get_open_travels_for_check(obj):
    included_statuses = [Travel.CERTIFICATION_SUBMITTED,
                         Travel.CERTIFICATION_APPROVED,
                         Travel.CERTIFICATION_REJECTED,
                         Travel.SENT_FOR_PAYMENT]
    return Travel.objects.filter(traveler=obj, status__in=included_statuses)
