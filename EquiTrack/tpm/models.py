__author__ = 'jcranwellward'

from django.db import models

from EquiTrack.utils import AdminURLMixin
from partners.models import GwPCALocation


class TPMVisit(AdminURLMixin, models.Model):

    PLANNED = u'planned'
    COMPLETED = u'completed'
    RESCHEDULED = u'rescheduled'
    TPM_STATUS = (
        (PLANNED, u"Planned"),
        (COMPLETED, u"Completed"),
        (RESCHEDULED, u"Rescheduled"),
    )

    pca = models.ForeignKey('partners.PCA')
    status = models.CharField(
        max_length=32L,
        choices=TPM_STATUS,
        default=PLANNED,
    )
    cycle_number = models.PositiveIntegerField(
        blank=True, null=True
    )
    pca_location = models.ForeignKey(
        'partners.GwPCALocation',
        blank=True, null=True
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
    assigned_by = models.ForeignKey(
        'auth.User'
    )

    class Meta:
        verbose_name = u'TPM Visit'
        verbose_name_plural = u'TPM Visits'

    def save(self, **kwargs):
        if self.completed_date:
            self.status = self.COMPLETED
        super(TPMVisit, self).save(**kwargs)


class PCALocation(GwPCALocation):

    class Meta:
        proxy = True
        verbose_name = u'PCA Location'
        verbose_name_plural = u'PCA Locations'