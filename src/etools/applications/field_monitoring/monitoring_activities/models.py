from django.conf import settings
from django.db import connection, models
from django.utils.translation import ugettext_lazy as _

from model_utils import Choices
from model_utils.models import TimeStampedModel
from unicef_locations.models import Location

from etools.applications.field_monitoring.planning.models import LocationSite
from etools.applications.partners.models import Intervention, PartnerOrganization
from etools.applications.reports.models import Result
from etools.applications.tpm.tpmpartners.models import TPMPartner
from etools.libraries.djangolib.models import SoftDeleteMixin


class MonitoringActivity(SoftDeleteMixin, TimeStampedModel):
    TYPES = Choices(
        ('staff', _('Staff')),
        ('tpm', _('TPM')),
    )

    activity_type = models.CharField(max_length=10, choices=TYPES)

    tpm_partner = models.ForeignKey(TPMPartner, blank=True, null=True, verbose_name=_('TPM Partner'),
                                    on_delete=models.CASCADE)
    team_members = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, verbose_name=_('Team Members'),
                                          related_name='monitoring_activities')
    person_responsible = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True,
                                           verbose_name=_('Person Responsible'), related_name='+',
                                           on_delete=models.SET_NULL)

    location = models.ForeignKey(Location, verbose_name=_('Location'), related_name='monitoring_activities',
                                 on_delete=models.CASCADE)
    location_site = models.ForeignKey(LocationSite, blank=True, null=True, verbose_name=_('Site'),
                                      related_name='monitoring_activities', on_delete=models.CASCADE)

    partners = models.ManyToManyField(PartnerOrganization, verbose_name=_('Partner'), related_name='+', blank=True)
    interventions = models.ManyToManyField(Intervention, verbose_name=_('PD/SSFA'), related_name='+', blank=True)
    cp_outputs = models.ManyToManyField(Result, verbose_name=_('Outputs'), related_name='+', blank=True)

    start_date = models.DateField(verbose_name=_('Start Date'), blank=True, null=True)
    end_date = models.DateField(verbose_name=_('End Date'), blank=True, null=True)

    class Meta:
        verbose_name = _('Monitoring Activity')
        verbose_name_plural = _('Monitoring Activities')
        ordering = ('id',)

    def __str__(self):
        return self.reference_number

    @property
    def reference_number(self):
        return '{}/{}/{}/FMA'.format(
            connection.tenant.country_short_code or '',
            self.created.year,
            self.id,
        )
