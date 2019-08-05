from unittest.mock import Mock, patch

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.tpm.tests.factories import TPMPartnerFactory
from etools.applications.tpm.tpmpartners.tasks import update_tpm_partners


class TestUpdateTpmPartners(BaseTenantTestCase):

    def _build_country(self, name):

        class CountryMock:

            def __init__(self, name):
                self.name = 'Country {}'.format(name.title())
                self.schema_name = name
                self.business_area_code = 'ZZZ {}'.format(name.title())
                self.vision_sync_enabled = True

            def __str__(self):
                return self.name

        return CountryMock(name)

    @patch('etools.applications.tpm.tpmpartners.tasks.logger', spec=['info', 'error'])
    @patch("etools.applications.tpm.tpmpartners.synchronizers.TPMPartnerSynchronizer.sync")
    @patch('etools.applications.vision.tasks.Country')
    def test_update_tpm_partners(self, country_rel, mock_send, logger):

        # create a country from a 'fake' class, creating a real country messes up a bunch of other tests
        country_mock = self._build_country('test_country')
        country_rel.objects.filter = Mock(return_value=[country_mock])
        country_rel.objects.get = Mock(return_value=country_mock)

        TPMPartnerFactory()

        update_tpm_partners()

        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(logger.info.call_count, 4)
