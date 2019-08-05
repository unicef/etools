from unittest.mock import Mock, patch

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.tpm.tests.factories import TPMPartnerFactory
from etools.applications.tpm.tpmpartners.tasks import update_tpm_partners
from etools.applications.users.models import Country
from etools.applications.users.tests.factories import CountryFactory


class TestUpdateTpmPartners(BaseTenantTestCase):

    def _build_country(self, name):
        """
        Given a name (e.g. 'test1'), creates a Country object via FactoryBoy. The object is not saved to the database.
        It exists only in memory. We must be careful not to save this because creating a new Country in the database
        complicates schemas.
        """
        country = CountryFactory.build(name='Country {}'.format(name.title()),
                                       schema_name=name,
                                       business_area_code='ZZZ {}'.format(name.title()))
        country.vision_sync_enabled = True
        # We'll want to check vision_last_synced as part of the tests, so set it to a known value.
        country.vision_last_synced = None
        # We mock save() so we can see if it was called or not, also to prevent database changes.
        country.save = Mock()

        return country

    @patch('etools.applications.tpm.tpmpartners.tasks.logger', spec=['info', 'error'])
    @patch("etools.applications.tpm.tpmpartners.synchronizers.TPMPartnerSynchronizer.sync")
    @patch('etools.applications.vision.tasks.Country')
    def test_update_tpm_partners(self, country_rel, mock_send, logger):

        country = self._build_country('test_country')
        Country.objects.filter = Mock(return_value=[country])
        Country.objects.get = Mock(return_value=country)

        TPMPartnerFactory()

        update_tpm_partners()

        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(logger.info.call_count, 4)
