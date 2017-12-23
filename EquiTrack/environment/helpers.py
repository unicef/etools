from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from environment.models import TenantFlag, TenantSwitch


def tenant_flag_is_active(request, flag_name):
    """
    Return True if this flag (flag_name) is active for the request provided.
    """
    flag = TenantFlag.get(flag_name)
    return flag.is_active(request)


def tenant_switch_is_active(switch_name):
    """
    Return True if this switch (switch_name) is active for the current tenant
    (based on db.connection.tenant). Return False in all other cases.
    """
    switch = TenantSwitch.get(switch_name)
    return switch.is_active()
