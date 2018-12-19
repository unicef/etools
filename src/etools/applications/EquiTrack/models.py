from django.db.models import Aggregate
from django_tenants.models import DomainMixin


class DSum(Aggregate):
    function = 'SUM'
    template = '%(function)s(DISTINCT %(expressions)s)'
    name = 'Sum'


class Domain(DomainMixin):
    """ Tenant Domain Model"""
