from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.http import JsonResponse
from features.models import TenantFlag


def get_flags(request):
    tenant = request.tenant
    tenant_flags = TenantFlag.objects.filter(countries=tenant)
    active_flags = [tenant_flag.flag.name for tenant_flag in tenant_flags]
    return JsonResponse({'active_flags': active_flags})
