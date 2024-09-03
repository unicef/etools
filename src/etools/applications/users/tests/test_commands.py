
from django.core.management import call_command
from django.core.management.base import CommandError

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.publics.tests.factories import PublicsCurrencyFactory
from etools.applications.users.models import Country


class TestAddCountry(BaseTenantTestCase):
    def test_command(self):
        # Not able to actually create a tenant, so checking
        # the raises exception that this is where the command
        # failed
        name = "test"
        PublicsCurrencyFactory(code="USD")
        with self.assertRaisesRegex(CommandError, "Can't create tenant"):
            call_command("add_country", name)

    def test_command_exception(self):
        country = Country.objects.first()
        with self.assertRaisesRegex(CommandError, "Currency matching query"):
            call_command("add_country", country.name)
