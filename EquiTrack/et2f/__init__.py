from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _



# THESE JUST FOR DEVELOPMENT - HAVE TO BE REMOVED - START

PULI_USER_USERNAME = 'puli'
PULI_USER_PASSWORD = 'lab'

# THESE JUST FOR DEVELOPMENT - HAVE TO BE REMOVED - END


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
    REJECTED = 'rejected'
    APPROVED = 'approved'
    CANCELLED = 'cancelled'
    SENT_FOR_PAYMENT = 'sent_for_payment'
    DONE = 'done'
    CERTIFICATION_SUBMITTED = 'certification_submitted'
    CERTIFICATION_APPROVED = 'certification_approved'
    CERTIFICATION_REJECTED = 'certification_rejected'
    CERTIFIED = 'certified'
    COMPLETED = 'completed'

    CHOICES = (
        (PLANNED, _('Planned')),
        (SUBMITTED, _('Submitted')),
        (REJECTED, _('Rejected')),
        (APPROVED, _('Approved')),
        (COMPLETED, _('Completed')),
        (CANCELLED, _('Cancelled')),
        (SENT_FOR_PAYMENT, _('Sent for payment')),
        (DONE, _('Done')),
        (CERTIFICATION_SUBMITTED, _('Certification submitted')),
        (CERTIFICATION_APPROVED, _('Certification approved')),
        (CERTIFICATION_REJECTED, _('Certification rejected')),
        (CERTIFIED, _('Certified')),
        (COMPLETED, _('Completed')),
    )