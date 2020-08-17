from datetime import timedelta

from django.utils import timezone

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import Intervention
from etools.applications.partners.tests.factories import AgreementFactory, InterventionFactory, PartnerFactory
from etools.applications.reports.tasks import transfer_active_pds_to_new_cp
from etools.applications.reports.tests.factories import CountryProgrammeFactory


class ActivePDTransferToNewCPTestCase(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.today = timezone.now().date()
        cls.old_cp = CountryProgrammeFactory(
            from_date=cls.today - timedelta(days=5),
            to_date=cls.today - timedelta(days=2),
        )
        cls.partner = PartnerFactory()
        cls.old_agreement = AgreementFactory(partner=cls.partner, country_programme=cls.old_cp)

    def _init_new_cp(self):
        self.active_cp = CountryProgrammeFactory(
            from_date=self.today - timedelta(days=1),
            to_date=self.today + timedelta(days=10),
        )

    def _init_new_agreement(self):
        self.new_agreement = AgreementFactory(partner=self.partner, country_programme=self.active_cp)

    def test_transfer_without_active_cp(self):
        pd = InterventionFactory(
            agreement=self.old_agreement,
            status=Intervention.ACTIVE,
            start=self.today - timedelta(days=4),
            end=self.today + timedelta(days=4)
        )

        transfer_active_pds_to_new_cp()

        pd.refresh_from_db()
        self.assertEqual(pd.agreement, self.old_agreement)

    def test_transfer_without_new_pca(self):
        pd = InterventionFactory(
            agreement=self.old_agreement,
            status=Intervention.ACTIVE,
            start=self.today - timedelta(days=4),
            end=self.today + timedelta(days=4)
        )
        self._init_new_cp()

        transfer_active_pds_to_new_cp()

        pd.refresh_from_db()
        self.assertEqual(pd.agreement, self.old_agreement)

    def test_transfer(self):
        pd = InterventionFactory(
            agreement=self.old_agreement,
            status=Intervention.ACTIVE,
            start=self.today - timedelta(days=4),
            end=self.today + timedelta(days=4)
        )
        self._init_new_cp()
        self._init_new_agreement()

        transfer_active_pds_to_new_cp()

        pd.refresh_from_db()
        self.assertEqual(pd.agreement, self.new_agreement)
