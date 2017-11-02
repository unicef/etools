from django.http import JsonResponse
from features.models import TenantFlag


def get_flags(request):
    tenant = request.tenant
    tenant_flags = TenantFlag.objects.filter(countries=tenant)
    active_flags = [tenant_flag.flag.name for tenant_flag in tenant_flags]
    return JsonResponse({'active_flags': active_flags})
