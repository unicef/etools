__author__ = 'jcranwellward'

from django.db import models

from EquiTrack.utils import AdminURLMixin


class TPMVisit(AdminURLMixin, models.Model):

    PLANNED = u'planned'
    COMPLETED = u'completed'
    CANCELLED = u'cancelled'
    TPM_STATUS = (
        (PLANNED, u"Planned"),
        (COMPLETED, u"Completed"),
        (CANCELLED, u"Cancelled"),
    )

    pca = models.ForeignKey('partners.PCA')
    status = models.CharField(
        max_length=32L,
        choices=TPM_STATUS,
        default=PLANNED,
    )
    location = models.ForeignKey(
        'locations.Location'
    )
    tentative_date = models.DateField(
        blank=True, null=True
    )
    completed_date = models.DateField(
        blank=True, null=True
    )
    comments = models.TextField(
        blank=True, null=True
    )