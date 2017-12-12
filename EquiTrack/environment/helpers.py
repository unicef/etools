from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from waffle.models import Flag, Switch


def tenant_flag_is_active(request, flag_name):
    """
    Return True if this flag (flag_name) is active for the request provided.

    This is a copy of waffle.flag_is_active, except that we first check the
    tenant before doing other checks.
    """
    flag = Flag.get(flag_name)
    if hasattr(flag, 'tenantflag'):
        return flag.tenantflag.is_active(request)
    else:
        return flag.is_active(request)


def tenant_switch_is_active(switch_name):
    """
    Return True if this switch (switch_name) is active for the current tenant
    (based on db.connection.tenant).

    This is a copy of waffle.switch_is_active, except that we ONLY check the
    tenant, and return False in all other cases.
    """
    switch = Switch.get(switch_name)
    if hasattr(switch, 'tenantswitch'):
        return switch.tenantswitch.is_active()
    return False
