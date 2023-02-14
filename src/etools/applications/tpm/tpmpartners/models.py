from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericRelation
from django.db import connection, models
from django.utils.translation import gettext_lazy as _

from unicef_attachments.models import Attachment

from etools.applications.firms.models import BaseFirm, BaseStaffMember


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

    def get_related_third_party_users(self):
        return get_user_model().objects.filter(models.Q(pk__in=self.staff_members.values_list('user_id')))


class TPMPartnerStaffMember(BaseStaffMember):
    tpm_partner = models.ForeignKey(
        TPMPartner, verbose_name=_('TPM Vendor'), related_name='staff_members',
        on_delete=models.CASCADE,
    )

    receive_tpm_notifications = models.BooleanField(
        verbose_name=_('Receive Notifications on TPM Tasks'), default=False)

    def __str__(self):
        return f'{self.get_full_name()} {self.tpm_partner} [{self.user.email}]'
