__author__ = 'jcranwellward'

from django.db import models
from django.core import urlresolvers

from funds.models import Grant
from reports.models import (
    IntermediateResult,
    Rrp5Output,
    Indicator,
    Activity,
    Sector,
    WBS,
)
from locations.models import (
    Governorate,
    GatewayType,
    Locality,
    Location,
    Region,
)


class PartnerOrganization(models.Model):

    name = models.CharField(max_length=45L)
    description = models.CharField(max_length=256L, blank=True)
    email = models.CharField(max_length=128L, blank=True)
    contact_person = models.CharField(max_length=64L, blank=True)
    phone_number = models.CharField(max_length=32L, blank=True)

    def __unicode__(self):
        return self.name


class PCA(models.Model):

    number = models.CharField(max_length=45L, blank=True)
    title = models.CharField(max_length=256L, blank=True)
    status = models.CharField(max_length=32L, blank=True)
    partner = models.ForeignKey(PartnerOrganization)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    initiation_date = models.DateField(null=True, blank=True)
    signed_by_unicef_date = models.DateField(null=True, blank=True)
    signed_by_partner_date = models.DateField(null=True, blank=True)
    unicef_mng_first_name = models.CharField(max_length=64L, blank=True)
    unicef_mng_last_name = models.CharField(max_length=64L, blank=True)
    unicef_mng_email = models.CharField(max_length=128L, blank=True)
    partner_mng_first_name = models.CharField(max_length=64L, blank=True)
    partner_mng_last_name = models.CharField(max_length=64L, blank=True)
    partner_mng_email = models.CharField(max_length=128L, blank=True)
    partner_contribution_budget = models.IntegerField(null=True, blank=True)
    unicef_cash_budget = models.IntegerField(null=True, blank=True)
    in_kind_amount_budget = models.IntegerField(null=True, blank=True)
    cash_for_supply_budget = models.IntegerField(null=True, blank=True)
    total_cash = models.IntegerField(null=True, blank=True, verbose_name='Total Budget')
    received_date = models.DateTimeField(null=True, blank=True)
    is_approved = models.NullBooleanField(null=True, blank=True)

    class Meta:
        verbose_name = 'PCA'
        verbose_name_plural = 'PCAs'

    def __unicode__(self):
        return u'{}: {}'.format(
            self.partner.name,
            self.number
        )

    def save(self, **kwargs):

        self.total_cash = (
            self.partner_contribution_budget +
            self.unicef_cash_budget +
            self.in_kind_amount_budget
        )
        super(PCA, self).save(**kwargs)


class PcaGrant(models.Model):
    pca = models.ForeignKey(PCA)
    grant = models.ForeignKey(Grant)
    funds = models.IntegerField(null=True, blank=True)

    def __unicode__(self):
        return self.grant


class GwPcaLocation(models.Model):

    pca = models.ForeignKey(PCA)
    name = models.CharField(max_length=128L)
    governorate = models.ForeignKey(Governorate, null=True, blank=True)
    region = models.ForeignKey(Region, null=True, blank=True)
    locality = models.ForeignKey(Locality, null=True, blank=True)
    gateway = models.ForeignKey(GatewayType, null=True, blank=True)
    location = models.ForeignKey(Location)

    def __unicode__(self):
        return self.location.p_code


class PCASector(models.Model):

    pca = models.ForeignKey(PCA)
    sector = models.ForeignKey(Sector)

    RRP5_outputs = models.ManyToManyField(Rrp5Output)
    activities = models.ManyToManyField(Activity)

    class Meta:
        verbose_name = 'PCA Sector'

    def __unicode__(self):
        return u'{}: {}: {}'.format(
            self.pca.partner.name,
            self.pca.number,
            self.sector.name,
        )

    def changeform_link(self):
        if self.id:
            url_name = 'admin:{app_label}_{model_name}_{action}'.format(
                app_label=self._meta.app_label,
                model_name=self._meta.module_name,
                action='change'
            )
            changeform_url = urlresolvers.reverse(url_name, args=(self.id,))
            return u'<a class="btn btn-primary default" ' \
                   u'href="{}" target="_blank">Details</a>'.format(changeform_url)
        return u''
    changeform_link.allow_tags = True
    changeform_link.short_description = ''   # omit column header


class PCASectorImmediateResult(models.Model):

    pca_sector = models.ForeignKey(PCASector)
    Intermediate_result = models.ForeignKey(IntermediateResult)

    wbs_activities = models.ManyToManyField(WBS)

    def __unicode__(self):
        return self.Intermediate_result.name


class IndicatorProgress(models.Model):

    pca_sector = models.ForeignKey(PCASector)
    indicator = models.ForeignKey(Indicator)
    programmed = models.IntegerField()
    current = models.IntegerField(blank=True, null=True)

    def __unicode__(self):
        return self.indicator.goal

    def shortfall(self):
        return self.programmed - self.current if self.id else ''
    shortfall.short_description = 'Shortfall'

    def unit(self):
        return self.indicator.unit.type if self.id else ''
    unit.short_description = 'Unit'


class PCAReport(models.Model):
    pca = models.ForeignKey(PCA)
    title = models.CharField(max_length=128L)
    description = models.CharField(max_length=512L)
    start_period = models.DateField(null=True, blank=True)
    end_period = models.DateField(null=True, blank=True)
    received_date = models.DateTimeField(null=True, blank=True)