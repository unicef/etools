from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.db import connection, models
from django.utils.encoding import python_2_unicode_compatible
from waffle.models import Flag, Switch

from users.models import Country


@python_2_unicode_compatible
class IssueCheckConfig(models.Model):
    """
    Used to enable/disable issue checks at runtime.
    """
    check_id = models.CharField(max_length=100, unique=True, db_index=True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return '{}: {}'.format(self.check_id, self.is_active)


@python_2_unicode_compatible
class TenantFlag(models.Model):
    """
    Associate one or more countries with a Flag.
    """
    countries = models.ManyToManyField(Country, blank=True, help_text=(
        'Activate this flag for these countries.'))
    flag = models.OneToOneField(Flag)

    def __str__(self):
        return self.flag.name

    def is_active(self, request):
        "Is this flag on for this tenant, or for any other reason?"
        if getattr(request, 'tenant', None) in self.countries.all():
            return True
        return self.flag.is_active(request)


@python_2_unicode_compatible
class TenantSwitch(models.Model):
    """
    Associate one or more countries with a Switch.
    """
    countries = models.ManyToManyField(Country, blank=True, help_text=(
        'Activate this switch for these countries.'))
    switch = models.OneToOneField(Switch)

    def __str__(self):
        return self.switch.name

    def is_active(self):
        "Is this switch on for this tenant?"
        if connection.tenant in self.countries.all():
            return self.switch.active
        return False
