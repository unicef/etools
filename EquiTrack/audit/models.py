from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from utils.organizations.models import BaseOrganization, BaseStaffMember


class AuditOrganization(BaseOrganization):
    pass


@python_2_unicode_compatible
class AuditOrganizationStaffMember(BaseStaffMember):
    audit_organization = models.ForeignKey(AuditOrganization, verbose_name=_('organization'), related_name='staff_members')

    def __str__(self):
        return '{} ({})'.format(
            self.get_full_name(),
            self.audit_organization.name
        )
