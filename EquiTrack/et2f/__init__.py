from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _


class BooleanChoice(object):
    NA = None
    YES = True
    NO = False

    CHOICES = (
        (NA, 'N/A'),
        (YES, 'Yes'),
        (NO, 'No')
    )


class TripStatus(object):
    PLANNED = 'planned'
    SUBMITTED = 'submitted'
    APPROVED = 'approved'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'

    CHOICES = (
        (PLANNED, _('Planned')),
        (SUBMITTED, _('Submitted')),
        (APPROVED, _('Approved')),
        (COMPLETED, _('Completed')),
        (CANCELLED, _('Cancelled')),
    )