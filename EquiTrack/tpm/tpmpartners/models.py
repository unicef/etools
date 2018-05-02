from django.contrib.contenttypes.fields import GenericRelation
from django.db import models, connection
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from attachments.models import Attachment
from firms.models import BaseFirm, BaseStaffMember


class TPMPartnerQueryset(models.QuerySet):
    def country_partners(self):
        if hasattr(connection.tenant, 'id'):
            return self.filter(countries=connection.tenant)
        else:
            return self


class TPMPartner(BaseFirm):
    countries = models.ManyToManyField('users.Country', blank=True)

    attachments = GenericRelation(Attachment, verbose_name=_('attachments'), blank=True)

    objects = models.Manager.from_queryset(TPMPartnerQueryset)()

    def activate(self, country):
        self.countries.add(country)

        if self.hidden:
            self.hidden = False
            self.save()


@python_2_unicode_compatible
class TPMPartnerStaffMember(BaseStaffMember):
    tpm_partner = models.ForeignKey(
        TPMPartner, verbose_name=_('TPM Vendor'), related_name='staff_members',
        on_delete=models.CASCADE,
    )

    receive_tpm_notifications = models.BooleanField(verbose_name=_('Receive Notifications on TPM Tasks'), default=False)

    def __str__(self):
        return self.get_full_name()
