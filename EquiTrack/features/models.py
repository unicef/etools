from __future__ import unicode_literals

from django.db import models
from waffle.models import Flag

from users.models import Country


class TenantFlag(models.Model):
    """
    Associate one or more countries with a Flag.
    """
    countries = models.ManyToManyField(Country, blank=True, help_text=(
        'Activate this flag for these countries.'))
    flag = models.OneToOneField(Flag)

    def is_active(self, request):
        "Is this flag on for this tenant, or for any other reason?"
        if request.tenant in self.countries.all():
            return True
        return self.flag.is_active(request)


def tenant_flag_is_active(request, flag_name):
    """
    Return True if this flag (flag_name) is active for the request provided.

    This is a copy of waffle.flag_is_active, except that we first check the
    tenant before doing other checks.
    """
    flag = Flag.get(flag_name)
    return flag.tenantflag.is_active(request)
