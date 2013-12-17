__author__ = 'jcranwellward'

from django.db import models
from django.core import urlresolvers

from filer.fields.file import FilerFileField

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

    name = models.CharField(max_length=45L, unique=True)
    description = models.CharField(max_length=256L, blank=True)
    email = models.CharField(max_length=128L, blank=True)
    contact_person = models.CharField(max_length=64L, blank=True)
    phone_number = models.CharField(max_length=32L, blank=True)

    def __unicode__(self):
        return self.name


class PCA(models.Model):

    PCA_STATUS = (
        (u'in_process', u"In Process"),
        (u'active', u"Active"),
        (u'implemented', u"Implemented"),
        (u'cancelled', u"Cancelled"),
    )

    number = models.CharField(max_length=45L, blank=True)
    title = models.CharField(max_length=256L)
    status = models.CharField(max_length=32L, blank=True, choices=PCA_STATUS, default=u'in_process')
    partner = models.ForeignKey(PartnerOrganization)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    initiation_date = models.DateField()
    signed_by_unicef_date = models.DateField(null=True, blank=True)
    signed_by_partner_date = models.DateField(null=True, blank=True)
    unicef_mng_first_name = models.CharField(max_length=64L, blank=True)
    unicef_mng_last_name = models.CharField(max_length=64L, blank=True)
    unicef_mng_email = models.CharField(max_length=128L, blank=True)
    partner_mng_first_name = models.CharField(max_length=64L, blank=True)
    partner_mng_last_name = models.CharField(max_length=64L, blank=True)
    partner_mng_email = models.CharField(max_length=128L, blank=True)
    partner_contribution_budget = models.IntegerField(null=True, blank=True, default=0)
    unicef_cash_budget = models.IntegerField(null=True, blank=True, default=0)
    in_kind_amount_budget = models.IntegerField(null=True, blank=True, default=0)
    cash_for_supply_budget = models.IntegerField(null=True, blank=True, default=0)
    total_cash = models.IntegerField(null=True, blank=True, verbose_name='Total Budget', default=0)

    # meta fields
    sectors = models.CharField(max_length=255, null=True, blank=True)
    amendment = models.BooleanField(default=False)
    current = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    versioned_at = models.DateTimeField(null=True)

    class Meta:
        verbose_name = 'PCA'
        verbose_name_plural = 'PCAs'

    def __unicode__(self):
        return u'{}: {}'.format(
            self.partner.name,
            self.number
        )

    def save(self, **kwargs):
        """
        Calculate total cash on save
        """
        if self.partner_contribution_budget \
            or self.unicef_cash_budget \
            or self.in_kind_amount_budget:
            self.total_cash = (
                self.partner_contribution_budget +
                self.unicef_cash_budget +
                self.in_kind_amount_budget
            )
        else:
            self.total_cash = 0

        if self.pcasector_set.all().count():
            self.sectors = ", ".join(
                [sector.sector.name for sector in self.pcasector_set.all()]
            )


        super(PCA, self).save(**kwargs)


class PCAGrant(models.Model):
    pca = models.ForeignKey(PCA)
    grant = models.ForeignKey(Grant)
    funds = models.IntegerField(null=True, blank=True)

    def __unicode__(self):
        return self.grant


class GwPCALocation(models.Model):

    pca = models.ForeignKey(PCA)
    name = models.CharField(max_length=128L)
    governorate = models.ForeignKey(Governorate, null=True, blank=True)
    region = models.ForeignKey(Region, null=True, blank=True)
    locality = models.ForeignKey(Locality, null=True, blank=True)
    gateway = models.ForeignKey(GatewayType, null=True, blank=True)
    location = models.ForeignKey(Location)

    class Meta:
        verbose_name = 'Activity Location'

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
                   u'onclick="return showAddAnotherPopup(this);" ' \
                   u'href="{}" target="_blank">Details</a>'.format(changeform_url)
        return u''
    changeform_link.allow_tags = True
    changeform_link.short_description = 'View Sector Details'


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


class FileType(models.Model):
    name = models.CharField(max_length=64L, unique=True)

    def __unicode__(self):
        return self.name


class PCAFile(models.Model):

    pca = models.ForeignKey(PCA)
    type = models.ForeignKey(FileType)
    file = FilerFileField()

    def __unicode__(self):
        return file.name

    def download_url(self):
        if self.file:
            return u'<a class="btn btn-primary default" ' \
                   u'href="{}" >Download</a>'.format(self.file.file.url)
        return u''
    download_url.allow_tags = True
    download_url.short_description = 'Download Files'


class PCAReport(models.Model):
    pca = models.ForeignKey(PCA)
    title = models.CharField(max_length=128L)
    description = models.CharField(max_length=512L)
    start_period = models.DateField(null=True, blank=True)
    end_period = models.DateField(null=True, blank=True)
    received_date = models.DateTimeField(null=True, blank=True)