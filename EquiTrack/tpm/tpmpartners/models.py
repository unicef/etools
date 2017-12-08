from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from attachments.models import Attachment
from firms.models import BaseFirm, BaseStaffMember


class TPMPartner(BaseFirm):
    attachments = GenericRelation(Attachment, verbose_name=_('attachments'), blank=True)


@python_2_unicode_compatible
class TPMPartnerStaffMember(BaseStaffMember):
    tpm_partner = models.ForeignKey(TPMPartner, verbose_name=_('TPM Vendor'), related_name='staff_members')

    receive_tpm_notifications = models.BooleanField(verbose_name=_('Receive Notifications on TPM Tasks'), default=False)

    def __str__(self):
        return self.get_full_name()