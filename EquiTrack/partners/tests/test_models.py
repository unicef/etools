import datetime

from tenant_schemas.test.cases import TenantTestCase

from EquiTrack.factories import PartnershipFactory, TripFactory, AgreementFactory
from funds.models import Donor, Grant
from reports.models import ResultStructure
from partners.models import (
    PCA,
    Agreement,
    AmendmentLog,
    FundingCommitment,
    PartnershipBudget,
    AgreementAmendmentLog,
)


class TestRefNumberGeneration(TenantTestCase):

    def setUp(self):
        self.date = datetime.date.today()
        self.tenant.country_short_code = 'LEBA'
        self.tenant.save()

        self.text = 'LEBA/{{}}{}01'.format(self.date.year)

    def test_pca_ref_generation(self):

        text = self.text.format('PCA')

        # test basic sequence
        agreement = AgreementFactory()
        self.assertEqual(agreement.reference_number, text)

        # create amendment
        AgreementAmendmentLog.objects.create(
            agreement=agreement,
            amended_at=self.date,
            status=PCA.ACTIVE
        )
        self.assertEqual(agreement.reference_number, text+'-01')

        # add another agreement
        agreement = AgreementFactory()
        self.assertEqual(agreement.reference_number, text[:-1]+'2')

    def test_other_agreement_types(self):

        for doc_type in [Agreement.MOU, Agreement.IC, Agreement.AWP, Agreement.SSFA]:
            agreement = AgreementFactory(agreement_type=doc_type)
            self.assertEqual(agreement.reference_number, self.text.format(doc_type))

    def test_pd_numbering(self):

        pd_ref = 'LEBA/PCA{year}01/{{}}{year}{{}}'.format(year=self.date.year)

        # create one programme document
        intervention = PartnershipFactory()
        self.assertEqual(intervention.reference_number, pd_ref.format('PD', '01'))

        # create another under the same partner and agreement
        intervention = PartnershipFactory(
            partner=intervention.partner,
            agreement=intervention.agreement
        )
        self.assertEqual(intervention.reference_number, pd_ref.format('PD', '02'))

        # create amendment
        AmendmentLog.objects.create(
            partnership=intervention,
            amended_at=self.date,
            status=PCA.ACTIVE
        )
        self.assertEqual(intervention.reference_number, pd_ref.format('PD', '02-01'))


class TestHACTCalculations(TenantTestCase):

    def setUp(self):
        year = datetime.date.today().year
        self.intervention = PartnershipFactory(
            status=u'active'
        )
        current_cp = ResultStructure.objects.create(
            name='Current Country Programme',
            from_date=datetime.date(year, 1, 1),
            to_date=datetime.date(year+1, 12, 31)
        )
        grant = Grant.objects.create(
            donor=Donor.objects.create(name='Test Donor'),
            name='SM12345678'
        )
        PartnershipBudget.objects.create(
            partnership=self.intervention,
            partner_contribution=10000,
            unicef_cash=60000,
            in_kind_amount=5000,
            year=str(year)
        )
        PartnershipBudget.objects.create(
            partnership=self.intervention,
            partner_contribution=10000,
            unicef_cash=40000,
            in_kind_amount=5000,
            year=str(year+1)
        )
        FundingCommitment.objects.create(
            start=current_cp.from_date,
            end=current_cp.from_date+datetime.timedelta(days=200),
            grant=grant,
            intervention=self.intervention,
            fr_number='0123456789',
            wbs='Test',
            fc_type='PCA',
            expenditure_amount=40000.00
        )
        FundingCommitment.objects.create(
            start=current_cp.from_date+datetime.timedelta(days=200),
            end=current_cp.to_date,
            grant=grant,
            intervention=self.intervention,
            fr_number='0123456789',
            wbs='Test',
            fc_type='PCA',
            expenditure_amount=40000.00
        )

    def test_planned_cash_transfers(self):

        total = self.intervention.partner.planned_cash_transfers
        self.assertEqual(total, 60000)

    def test_actual_cash_transferred(self):
        total = self.intervention.partner.actual_cash_transferred
        self.assertEqual(total, 40000)

    def test_total_cash_transferred(self):
        total = self.intervention.partner.total_cash_transferred
        self.assertEqual(total, 80000)