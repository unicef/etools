from unittest.mock import Mock, patch

from django.core.management import call_command

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.users.models import Country

COUNTRY_PATH = "etools.applications.t2f.management.commands.et2f_init.UserCountry.objects.get"


class TestET2FInitCommand(BaseTenantTestCase):
    def test_command(self):
        mock_country = Mock(return_value=Country.objects.first())
        with patch(COUNTRY_PATH, mock_country):
            call_command("et2f_init", "admin", "123")
