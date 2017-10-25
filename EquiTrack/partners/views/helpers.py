from django.db import connection
from rest_framework.exceptions import ValidationError
from users.models import Country


def set_tenant_or_fail(workspace):
    """
    Sets the tenant for a workspace (Country) or raises a ValidationError if not able to
    """
    if workspace is None:
        raise ValidationError('Workspace is required as a queryparam')
    else:
        try:
            ws = Country.objects.exclude(name__in=['Global']).get(business_area_code=workspace)
        except Country.DoesNotExist:
            raise ValidationError('Workspace code provided is not a valid business_area_code: %s' % workspace)
        else:
            connection.set_tenant(ws)
