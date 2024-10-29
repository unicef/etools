import warnings

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericRelation
from django.db import connection, models
from django.utils.translation import gettext_lazy as _

from unicef_attachments.models import Attachment

from etools.applications.firms.models import BaseFirm, BaseFirmManager, BaseStaffMember
from etools.applications.users.mixins import TPM_ACTIVE_GROUPS


class TPMPartnerQueryset(models.QuerySet):
    def country_partners(self):
        if hasattr(connection.tenant, 'id'):
            return self.filter(countries=connection.tenant)
        else:
            return self


class TPMPartner(BaseFirm):
    countries = models.ManyToManyField('users.Country', blank=True)

    attachments = GenericRelation(Attachment, verbose_name=_('attachments'), blank=True)

    objects = BaseFirmManager.from_queryset(TPMPartnerQueryset)()

    def activate(self, country):
        self.countries.add(country)

        if self.hidden:
            self.hidden = False
            self.save()

    @property
    def staff_members(self) -> models.QuerySet:
        return get_user_model().objects.filter(
            pk__in=self.organization.realms.filter(
                is_active=True,
                country=connection.tenant,
                group__name__in=TPM_ACTIVE_GROUPS,
            ).values_list('user_id', flat=True)
        )

    @property
    def all_staff_members(self) -> models.QuerySet:
        return get_user_model().objects.filter(
            pk__in=self.organization.realms.filter(
                country=connection.tenant,
                group__name__in=TPM_ACTIVE_GROUPS,
            ).values_list('user_id', flat=True)
        )

    def get_related_third_party_users(self):
        return self.staff_members.filter(
            realms__organization=self.organization,
            realms__is_active=True,
        )


class TPMPartnerStaffMember(BaseStaffMember):
    """
    legacy tpm staff member model - shouldn't be used
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        warnings.warn('TPMPartnerStaffMember was deprecated in favor of Realms')

    tpm_partner = models.ForeignKey(
        TPMPartner, verbose_name=_('TPM Vendor'), related_name='old_staff_members',
        on_delete=models.CASCADE,
    )

    receive_tpm_notifications = models.BooleanField(
        verbose_name=_('Receive Notifications on TPM Tasks'), default=False)

    def __str__(self):
        return f'{self.get_full_name()} {self.tpm_partner} [{self.user.email}]'
