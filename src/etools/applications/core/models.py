from django_tenants.models import DomainMixin


class Domain(DomainMixin):
    """ Tenant Domain Model"""

    def __str__(self):
        return f'{self.domain} [{self.tenant.schema_name}]'
