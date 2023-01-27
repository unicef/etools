from django.db import connection, models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from model_utils import Choices
from model_utils.models import TimeStampedModel


class OrganizationType:
    BILATERAL_MULTILATERAL = "Bilateral / Multilateral"
    CIVIL_SOCIETY_ORGANIZATION = "Civil Society Organization"
    GOVERNMENT = "Government"
    UN_AGENCY = "UN Agency"

    CHOICES = Choices(
        (BILATERAL_MULTILATERAL, _(BILATERAL_MULTILATERAL)),
        (CIVIL_SOCIETY_ORGANIZATION, _(CIVIL_SOCIETY_ORGANIZATION)),
        (GOVERNMENT, _(GOVERNMENT)),
        (UN_AGENCY, _(UN_AGENCY)),
    )


class OrganizationManager(models.Manager):
    def get_by_natural_key(self, vendor_number):
        return self.get(vendor_number=vendor_number)


class Organization(TimeStampedModel, models.Model):

    CSO_TYPE_INTERNATIONAL = "International"
    CSO_TYPE_NATIONAL = "National"
    CSO_TYPE_COMMUNITY = "Community Based Organization"
    CSO_TYPE_ACADEMIC = "Academic Institution"
    CSO_TYPE_REDCROSS = 'Red Cross/Red Crescent National Societies'
    CSO_TYPES = Choices(
        (CSO_TYPE_INTERNATIONAL, _(CSO_TYPE_INTERNATIONAL)),
        (CSO_TYPE_NATIONAL, _(CSO_TYPE_NATIONAL)),
        (CSO_TYPE_COMMUNITY, _(CSO_TYPE_COMMUNITY)),
        (CSO_TYPE_ACADEMIC, _(CSO_TYPE_ACADEMIC)),
        (CSO_TYPE_REDCROSS, _('Red Cross/Red Crescent National Societies')),
    )
    parent = models.ForeignKey(
        'self',
        verbose_name=_('Parent Organization'),
        null=True, blank=True,
        related_name='children',
        db_index=True,
        on_delete=models.CASCADE
    )
    name = models.CharField(
        verbose_name=_("Vendor Name"),
        max_length=255,
        null=True,
        blank=True
    )
    vendor_number = models.CharField(
        verbose_name=_("Vendor Number"),
        max_length=30,
        unique=True
    )
    organization_type = models.CharField(
        verbose_name=_("Organization Type"),
        max_length=50,
        choices=OrganizationType.CHOICES,
        null=True,
        blank=True
    )
    # this is only applicable if type is CSO
    cso_type = models.CharField(
        verbose_name=_("CSO Type"),
        max_length=50,
        choices=CSO_TYPES,
        null=True,
        blank=True
    )
    short_name = models.CharField(
        verbose_name=_("Short Name"),
        max_length=50,
        null=True,
        blank=True
    )
    other = models.JSONField(
        verbose_name=_("Other Details"),
        null=True,
        blank=True
    )

    objects = OrganizationManager()

    class Meta:
        ordering = ("name",)
        verbose_name = _("Organization")
        verbose_name_plural = _("Organizations")
        unique_together = ('name', 'vendor_number')

    def __str__(self):
        return self.name if self.name else self.vendor_number

    @cached_property
    def relationship_types(self):
        _list = []
        if hasattr(self, 'partner') and \
                not self.partner.hidden:
            _list.append('partner')
        elif hasattr(self, 'auditorfirm') and \
                self.auditorfirm.purchase_orders.filter(engagement__isnull=False).exists() and \
                not self.auditorfirm.hidden:
            _list.append('audit')
        elif hasattr(self, 'tpmpartner') and \
                self.tpmpartner.countries.filter(id=connection.tenant.id).exists() and \
                not self.tpmpartner.hidden:
            _list.append('tpm')
        return _list
