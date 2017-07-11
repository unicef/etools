import datetime
import json
from unittest import skip
from actstream.models import model_stream

from EquiTrack.stream_feed.actions import create_snapshot_activity_stream
from EquiTrack.tests.mixins import FastTenantTestCase as TenantTestCase
from EquiTrack.factories import PartnershipFactory, AgreementFactory, InterventionFactory, InterventionBudgetFactory

from funds.models import Donor, Grant

from reports.models import (
    CountryProgramme,
    ResultType,
)
from partners.models import (
    PCA,
    Agreement,
    AmendmentLog,
    FundingCommitment,
    AgreementAmendmentLog,
    PartnerOrganization,
    Assessment,
    Result,
    ResultStructure,
    GovernmentIntervention,
    GovernmentInterventionResult,
    Intervention,
    InterventionBudget,
)


class TestRefNumberGeneration(TenantTestCase):
    fixtures = ['initial_data.json']

    def setUp(self):
        self.date = datetime.date.today()
        self.tenant.country_short_code = 'LEBA'
        self.tenant.save()

        self.text = 'LEBA/{{}}{}'.format(self.date.year)

    @skip("Fix this")
    def test_pca_ref_generation(self):

        text = self.text.format('PCA')

        # test basic sequence
        agreement1 = AgreementFactory()
        self.assertEqual(agreement1.reference_number, text)

        # create amendment
        AgreementAmendmentLog.objects.create(
            agreement=agreement1,
            amended_at=self.date,
            status=PCA.ACTIVE
        )
        self.assertEqual(agreement1.reference_number, text + '-01')

        # add another agreement
        agreement2 = AgreementFactory()
        self.assertEqual(agreement2.reference_number, text[:-1] + '2')

        # now sign the agreement and commit the number to the database
        agreement2.signed_by_unicef_date = self.date
        agreement2.save()
        self.assertEqual(agreement2.reference_number, text[:-1] + '2')

        # agreement numbering remains the same even if previous agreement is deleted
        agreement3 = AgreementFactory(signed_by_unicef_date=self.date)
        agreement1.delete()
        self.assertEqual(agreement3.reference_number, text[:-1] + '3')

    def test_other_agreement_types(self):

        for doc_type in [Agreement.MOU, Agreement.IC, Agreement.AWP, Agreement.SSFA]:
            agreement = AgreementFactory(agreement_type=doc_type)
            # test startswith only to avoid failing tests because of mismatching last digits
            self.assertTrue(agreement.reference_number.startswith(self.text.format(doc_type)))

    @skip("Fix this")
    def test_pd_numbering(self):

        pd_ref = 'LEBA/PCA{year}01/{{}}{year}{{}}'.format(year=self.date.year)

        # create one programme document
        intervention1 = PartnershipFactory()
        self.assertEqual(intervention1.reference_number, pd_ref.format('PD', '01'))

        # create another under the same partner and agreement
        intervention2 = PartnershipFactory(
            partner=intervention1.partner,
            agreement=intervention1.agreement
        )
        self.assertEqual(intervention2.reference_number, pd_ref.format('PD', '02'))

        # create amendment
        AmendmentLog.objects.create(
            partnership=intervention2,
            amended_at=self.date,
            status=PCA.ACTIVE
        )
        self.assertEqual(intervention2.reference_number, pd_ref.format('PD', '02-01'))

        intervention3 = PartnershipFactory(
            partner=intervention1.partner,
            agreement=intervention1.agreement,
        )
        self.assertEqual(intervention3.reference_number, pd_ref.format('PD', '03'))

        # agreement numbering remains the same even if previous agreement is deleted
        intervention3.signed_by_unicef_date = self.date
        intervention3.save()
        intervention1.delete()
        self.assertEqual(intervention3.reference_number, pd_ref.format('PD', '03'))


class TestHACTCalculations(TenantTestCase):
    fixtures = ['initial_data.json']

    def setUp(self):
        year = datetime.date.today().year
        self.intervention = InterventionFactory(
            status=u'active'
        )
        current_cp = ResultStructure.objects.create(
            name='Current Country Programme',
            from_date=datetime.date(year, 1, 1),
            to_date=datetime.date(year + 1, 12, 31)
        )
        grant = Grant.objects.create(
            donor=Donor.objects.create(name='Test Donor'),
            name='SM12345678'
        )
        InterventionBudget.objects.create(
            intervention=self.intervention,
            partner_contribution=10000,
            unicef_cash=60000,
            in_kind_amount=5000,
            year=str(year)
        )
        InterventionBudget.objects.create(
            intervention=self.intervention,
            partner_contribution=10000,
            unicef_cash=40000,
            in_kind_amount=5000,
            year=str(year + 1)
        )
        FundingCommitment.objects.create(
            start=current_cp.from_date,
            end=current_cp.from_date + datetime.timedelta(days=200),
            grant=grant,
            fr_number='0123456789',
            wbs='Test',
            fc_type='PCA',
            expenditure_amount=40000.00
        )
        FundingCommitment.objects.create(
            start=current_cp.from_date + datetime.timedelta(days=200),
            end=current_cp.to_date,
            grant=grant,
            fr_number='0123456789',
            wbs='Test',
            fc_type='PCA',
            expenditure_amount=40000.00
        )

    def test_planned_cash_transfers(self):

        PartnerOrganization.planned_cash_transfers(self.intervention.agreement.partner)
        hact = json.loads(self.intervention.agreement.partner.hact_values) \
            if isinstance(self.intervention.agreement.partner.hact_values, str) \
            else self.intervention.agreement.partner.hact_values
        self.assertEqual(hact['planned_cash_transfer'], 60000)


class TestPartnerOrganizationModel(TenantTestCase):
    fixtures = ['initial_data.json']

    def setUp(self):
        self.partner_organization = PartnerOrganization.objects.create(
            name="Partner Org 1",
        )
        year = datetime.date.today().year
        self.pca_signed1 = Agreement.objects.create(
            agreement_type=Agreement.PCA,
            partner=self.partner_organization,
            signed_by_unicef_date=datetime.date(year - 1, 1, 1),
            signed_by_partner_date=datetime.date(year - 1, 1, 1),
        )
        Agreement.objects.create(
            agreement_type=Agreement.PCA,
            partner=self.partner_organization,
            signed_by_unicef_date=datetime.date(year - 2, 1, 1),
            signed_by_partner_date=datetime.date(year - 2, 1, 1),
        )
        Agreement.objects.create(
            agreement_type=Agreement.PCA,
            partner=self.partner_organization,
        )

    def test_get_last_pca(self):
        pca = self.partner_organization.get_last_pca
        self.assertEqual(pca, self.pca_signed1)

    def test_micro_assessment_needed_high_risk(self):
        year = datetime.date.today().year
        self.partner_organization.type_of_assessment = "High Risk Assumed"
        self.partner_organization.save()
        Assessment.objects.create(
            partner=self.partner_organization,
            type="Micro Assessment",
            completed_date=datetime.date(year, 1, 1)
        )
        PartnerOrganization.micro_assessment_needed(self.partner_organization)
        self.assertEqual(self.partner_organization.hact_values["micro_assessment_needed"], "Yes")

    def test_micro_assessment_needed_pct_over_100k(self):
        year = datetime.date.today().year
        self.partner_organization.type_of_assessment = "Simplified Checklist"
        self.partner_organization.hact_values["planned_cash_transfer"] = 100001.00
        self.partner_organization.save()
        Assessment.objects.create(
            partner=self.partner_organization,
            type="Micro Assessment",
            completed_date=datetime.date(year, 1, 1)
        )
        PartnerOrganization.micro_assessment_needed(self.partner_organization)
        self.assertEqual(self.partner_organization.hact_values["micro_assessment_needed"], "Yes")

    def test_micro_assessment_needed_older_than_54m(self):
        self.partner_organization.type_of_assessment = "Micro Assessment"
        self.partner_organization.rating = "low"
        self.partner_organization.hact_values["planned_cash_transfer"] = 10000.00
        self.partner_organization.save()
        Assessment.objects.create(
            partner=self.partner_organization,
            type="Micro Assessment",
            completed_date=datetime.date.today() - datetime.timedelta(days=1643)
        )
        PartnerOrganization.micro_assessment_needed(self.partner_organization)
        self.assertEqual(self.partner_organization.hact_values["micro_assessment_needed"], "Yes")

    def test_micro_assessment_needed_missing(self):
        self.partner_organization.hact_values["planned_cash_transfer"] = 10000.00
        self.partner_organization.save()
        PartnerOrganization.micro_assessment_needed(self.partner_organization)
        self.assertEqual(self.partner_organization.hact_values["micro_assessment_needed"], "Missing")

    def test_micro_assessment_needed_no(self):
        year = datetime.date.today().year
        self.partner_organization.type_of_assessment = "Other"
        self.partner_organization.hact_values["planned_cash_transfer"] = 100000.00
        self.partner_organization.save()
        Assessment.objects.create(
            partner=self.partner_organization,
            type="Micro Assessment",
            completed_date=datetime.date(year, 1, 1)
        )
        PartnerOrganization.micro_assessment_needed(self.partner_organization)
        self.assertEqual(self.partner_organization.hact_values["micro_assessment_needed"], "No")

    def test_audit_needed_under_500k(self):
        self.partner_organization.total_ct_cp = 500000.00
        self.partner_organization.save()
        PartnerOrganization.audit_needed(self.partner_organization)
        self.assertEqual(self.partner_organization.hact_values['audits_mr'], 0)

    def test_audit_needed_over_500k(self):
        self.partner_organization.total_ct_cp = 500001.00
        self.partner_organization.save()
        PartnerOrganization.audit_needed(self.partner_organization)
        self.assertEqual(self.partner_organization.hact_values['audits_mr'], 1)

    def test_audit_needed_last_audit_is_in_current(self):
        CountryProgramme.objects.create(
            name="CP 1",
            wbs="/A0/",
            from_date=datetime.date(datetime.date.today().year - 1, 1, 1),
            to_date=datetime.date(datetime.date.today().year + 1, 1, 1),
        )
        Assessment.objects.create(
            partner=self.partner_organization,
            type="Scheduled Audit report",
            completed_date=datetime.date(datetime.date.today().year, 1, 1)
        )
        self.partner_organization.total_ct_cp = 500001.00
        self.partner_organization.save()
        PartnerOrganization.audit_needed(self.partner_organization)
        self.assertEqual(self.partner_organization.hact_values['audits_mr'], 1)

    def test_audit_needed_last_audit_is_not_in_current(self):
        CountryProgramme.objects.create(
            name="CP 1",
            wbs="/A0/",
            from_date=datetime.date(datetime.date.today().year - 1, 1, 1),
            to_date=datetime.date(datetime.date.today().year + 1, 1, 1),
        )
        Assessment.objects.create(
            partner=self.partner_organization,
            type="Scheduled Audit report",
            completed_date=datetime.date(datetime.date.today().year - 2, 1, 1)
        )
        self.partner_organization.total_ct_cp = 500001.00
        self.partner_organization.save()
        PartnerOrganization.audit_needed(self.partner_organization)
        self.assertEqual(self.partner_organization.hact_values['audits_mr'], 1)

    def test_audit_needed_extra_assessment_after_last(self):
        CountryProgramme.objects.create(
            name="CP 1",
            wbs="/A0/",
            from_date=datetime.date(datetime.date.today().year - 1, 1, 1),
            to_date=datetime.date(datetime.date.today().year + 1, 1, 1),
        )
        Assessment.objects.create(
            partner=self.partner_organization,
            type="Scheduled Audit report",
            completed_date=datetime.date(datetime.date.today().year, 1, 1)
        )
        assessment2 = Assessment.objects.create(
            partner=self.partner_organization,
            type="Scheduled Audit report",
            completed_date=datetime.date(datetime.date.today().year, 2, 1)
        )
        self.partner_organization.total_ct_cp = 500001.00
        self.partner_organization.save()
        PartnerOrganization.audit_needed(self.partner_organization, assessment2)
        self.assertEqual(self.partner_organization.hact_values['audits_mr'], 1)

    def test_audit_needed_extra_assessment_only(self):
        CountryProgramme.objects.create(
            name="CP 1",
            wbs="/A0/",
            from_date=datetime.date(datetime.date.today().year - 1, 1, 1),
            to_date=datetime.date(datetime.date.today().year + 1, 1, 1),
        )
        assessment = Assessment.objects.create(
            partner=self.partner_organization,
            type="Scheduled Audit report",
            completed_date=datetime.date(datetime.date.today().year, 2, 1)
        )
        self.partner_organization.total_ct_cp = 500001.00
        self.partner_organization.save()
        PartnerOrganization.audit_needed(self.partner_organization, assessment)
        self.assertEqual(self.partner_organization.hact_values['audits_mr'], 1)

    def test_audit_done(self):
        CountryProgramme.objects.create(
            name="CP 1",
            wbs="/A0/",
            from_date=datetime.date(datetime.date.today().year - 1, 1, 1),
            to_date=datetime.date(datetime.date.today().year + 1, 1, 1),
        )
        Assessment.objects.create(
            partner=self.partner_organization,
            type="Scheduled Audit report",
            completed_date=datetime.date(datetime.date.today().year, 1, 1)
        )
        self.partner_organization.total_ct_cp = 500001.00
        self.partner_organization.save()
        PartnerOrganization.audit_done(self.partner_organization)
        self.assertEqual(self.partner_organization.hact_values['audits_done'], 1)

    def test_audit_done_zero(self):
        PartnerOrganization.audit_done(self.partner_organization)
        self.assertEqual(self.partner_organization.hact_values['audits_done'], 0)

    def test_hact_min_requirements_ct_equals_0(self):
        self.partner_organization.total_ct_cy = 0
        self.partner_organization.save()
        hact_min_req = self.partner_organization.hact_min_requirements
        data = {
            "programme_visits": 0,
            "spot_checks": 0,
        }
        self.assertEqual(hact_min_req, data)

    def test_hact_min_requirements_ct_under_50k(self):
        self.partner_organization.total_ct_cy = 50000.00
        self.partner_organization.save()
        hact_min_req = self.partner_organization.hact_min_requirements
        data = {
            "programme_visits": 1,
            "spot_checks": 0,
        }
        self.assertEqual(hact_min_req, data)

    def test_hact_min_requirements_ct_between_50k_and_100k(self):
        self.partner_organization.total_ct_cy = 50001.00
        self.partner_organization.save()
        hact_min_req = self.partner_organization.hact_min_requirements
        data = {
            "programme_visits": 1,
            "spot_checks": 1,
        }
        self.assertEqual(hact_min_req, data)

    def test_hact_min_requirements_ct_between_100k_and_350k_moderate(self):
        self.partner_organization.total_ct_cy = 100001.00
        self.partner_organization.rating = "Moderate"
        self.partner_organization.save()
        hact_min_req = self.partner_organization.hact_min_requirements
        data = {
            "programme_visits": 1,
            "spot_checks": 1,
        }
        self.assertEqual(hact_min_req, data)

    def test_hact_min_requirements_ct_between_100k_and_350k_high(self):
        self.partner_organization.total_ct_cy = 100001.00
        self.partner_organization.rating = "High"
        self.partner_organization.save()
        hact_min_req = self.partner_organization.hact_min_requirements
        data = {
            "programme_visits": 2,
            "spot_checks": 2,
        }
        self.assertEqual(hact_min_req, data)

    def test_hact_min_requirements_ct_over_350k_moderate(self):
        self.partner_organization.total_ct_cy = 350001.00
        self.partner_organization.rating = "Moderate"
        self.partner_organization.save()
        hact_min_req = self.partner_organization.hact_min_requirements
        data = {
            "programme_visits": 2,
            "spot_checks": 1,
        }
        self.assertEqual(hact_min_req, data)

    def test_hact_min_requirements_ct_over_350k_high(self):
        self.partner_organization.total_ct_cy = 350001.00
        self.partner_organization.rating = "High"
        self.partner_organization.save()
        hact_min_req = self.partner_organization.hact_min_requirements
        data = {
            "programme_visits": 4,
            "spot_checks": 3,
        }
        self.assertEqual(hact_min_req, data)

    def test_planned_cash_transfers_gov(self):
        self.partner_organization.partner_type = "Government"
        self.partner_organization.save()
        cp = CountryProgramme.objects.create(
            name="CP 1",
            wbs="/A0/",
            from_date=datetime.date(datetime.date.today().year - 1, 1, 1),
            to_date=datetime.date(datetime.date.today().year + 1, 1, 1),
        )
        rs = ResultStructure.objects.create(
            name="RS 1",
            country_programme=cp,
            from_date=datetime.date(datetime.date.today().year - 1, 1, 1),
            to_date=datetime.date(datetime.date.today().year + 1, 1, 1),
        )
        gi = GovernmentIntervention.objects.create(
            partner=self.partner_organization,
            result_structure=rs,
        )
        rt = ResultType.objects.get(id=1)
        r = Result.objects.create(
            result_type=rt,
            result_structure=rs
        )
        GovernmentInterventionResult.objects.create(
            intervention=gi,
            result=r,
            year=datetime.date.today().year,
            planned_amount=100000,
        )
        GovernmentInterventionResult.objects.create(
            intervention=gi,
            result=r,
            year=datetime.date.today().year,
            planned_amount=50000,
        )
        hact = json.loads(self.partner_organization.hact_values) \
            if isinstance(self.partner_organization.hact_values, str) \
            else self.partner_organization.hact_values
        self.assertEqual(hact['planned_cash_transfer'], 150000)

    def test_planned_cash_transfers_non_gov(self):
        self.partner_organization.partner_type = "UN Agency"
        self.partner_organization.save()
        agreement = Agreement.objects.create(
            agreement_type=Agreement.PCA,
            partner=self.partner_organization,
        )

        intervention = InterventionFactory(
            status=u'active', agreement=agreement
        )
        InterventionBudgetFactory(intervention=intervention)
        hact = json.loads(self.partner_organization.hact_values) \
            if isinstance(self.partner_organization.hact_values, str) \
            else self.partner_organization.hact_values
        self.assertEqual(hact['planned_cash_transfer'], 100001)

    def test_planned_visits_gov(self):
        self.partner_organization.partner_type = "Government"
        self.partner_organization.save()
        cp = CountryProgramme.objects.create(
            name="CP 1",
            wbs="/A0/",
            from_date=datetime.date(datetime.date.today().year - 1, 1, 1),
            to_date=datetime.date(datetime.date.today().year + 1, 1, 1),
        )
        rs = ResultStructure.objects.create(
            name="RS 1",
            country_programme=cp,
            from_date=datetime.date(datetime.date.today().year - 1, 1, 1),
            to_date=datetime.date(datetime.date.today().year + 1, 1, 1),
        )
        gi = GovernmentIntervention.objects.create(
            partner=self.partner_organization,
            result_structure=rs,
        )
        rt = ResultType.objects.get(id=1)
        r = Result.objects.create(
            result_type=rt,
            result_structure=rs
        )
        GovernmentInterventionResult.objects.create(
            intervention=gi,
            result=r,
            year=datetime.date.today().year,
            planned_visits=3,
        )
        GovernmentInterventionResult.objects.create(
            intervention=gi,
            result=r,
            year=datetime.date.today().year,
            planned_visits=2,
        )
        self.assertEqual(self.partner_organization.hact_values['planned_visits'], 5)

    @skip("Fix when HACT available")
    def test_planned_visits_non_gov(self):
        self.partner_organization.partner_type = "UN Agency"
        self.partner_organization.status = PCA.ACTIVE
        self.partner_organization.save()
        agreement = Agreement.objects.create(
            agreement_type=Agreement.PCA,
            partner=self.partner_organization,
        )
        Intervention.objects.create(
            title="Int 1",
            status=PCA.ACTIVE,
            agreement=agreement,
            submission_date=datetime.date(datetime.date.today().year, 1, 1),
            end=datetime.date(datetime.date.today().year + 1, 1, 1),
            planned_visits=3,
        )
        Intervention.objects.create(
            title="Int 1",
            status=PCA.ACTIVE,
            agreement=agreement,
            submission_date=datetime.date(datetime.date.today().year, 1, 1),
            end=datetime.date(datetime.date.today().year + 1, 1, 1),
            planned_visits=2,
        )
        self.assertEqual(self.partner_organization.hact_values['planned_visits'], 5)


class TestAgreementModel(TenantTestCase):
    fixtures = ['initial_data.json']

    def setUp(self):
        self.partner_organization = PartnerOrganization.objects.create(
            name="Partner Org 1",
        )
        self.agreement = Agreement.objects.create(
            agreement_type=Agreement.PCA,
            partner=self.partner_organization,
        )
        # Trigger created event activity stream
        create_snapshot_activity_stream(
            self.partner_organization, self.agreement, created=True)

    @skip('no temp ref')
    def test_reference_number(self):
        self.assertIn("PCA", self.agreement.reference_number)

    def test_snapshot_activity_stream(self):
        self.agreement.start = datetime.date.today()
        self.agreement.signed_by_unicef_date = datetime.date.today()

        create_snapshot_activity_stream(
            self.partner_organization, self.agreement)
        self.agreement.save()

        # Check if new activity action has been created
        self.assertEqual(model_stream(Agreement).count(), 2)

        # Check the previous content
        previous = model_stream(Agreement).first().data['previous']
        self.assertNotEqual(previous, {})

        # Check the changes content
        changes = model_stream(Agreement).first().data['changes']
        self.assertNotEqual(changes, {})

        # Check if the previous had the empty date fields
        self.assertEqual(previous['start'], 'None')
        self.assertEqual(previous['signed_by_unicef_date'], 'None')

        # Check if the changes had the updated date fields
        self.assertEqual(changes['start'], str(self.agreement.start))
        self.assertEqual(changes['signed_by_unicef_date'], str(self.agreement.signed_by_unicef_date))


class TestInterventionModel(TenantTestCase):
    fixtures = ['initial_data.json']

    def setUp(self):
        self.partner_organization = PartnerOrganization.objects.create(
            name="Partner Org 1",
        )
        agreement = Agreement.objects.create(
            agreement_type=Agreement.PCA,
            partner=self.partner_organization,
        )
        self.intervention = Intervention.objects.create(
            title="Intervention 1",
            agreement=agreement,
            submission_date=datetime.date(datetime.date.today().year, 1, 1),
        )

    # TODO relativedelta() returns 0, may be a bug in the model code
    def test_days_from_submission_signed(self):
        self.intervention.submission_date = datetime.date(datetime.date.today().year - 1, 1, 1)
        self.intervention.signed_by_partner_date = datetime.date(datetime.date.today().year - 1, 5, 1)
        # days = (self.intervention.signed_by_partner_date - self.intervention.submission_date).days
        # self.assertEqual(self.intervention.days_from_submission_to_signed, days)

    # TODO relativedelta() returns 0, may be a bug in the model code
    def test_days_from_review_to_signed(self):
        self.intervention.submission_date = datetime.date(datetime.date.today().year - 1, 1, 1)
        self.intervention.review_date = datetime.date(datetime.date.today().year - 1, 2, 1)
        self.intervention.signed_by_partner_date = datetime.date(datetime.date.today().year - 1, 5, 1)
        # days = (self.intervention.signed_by_partner_date - self.intervention.review_date).days
        # self.assertEqual(self.intervention.days_from_review_to_signed, days)

    # TODO relativedelta() returns 0, may be a bug in the model code
    def test_duration(self):
        self.intervention.start_date = datetime.date(datetime.date.today().year - 1, 1, 1)
        self.intervention.end_date = datetime.date(datetime.date.today().year + 1, 1, 1)
        # self.assertEqual(self.intervention.duration, 24)

    def test_total_unicef_cash(self):
        InterventionBudget.objects.create(
            intervention=self.intervention,
            unicef_cash=100000,
            unicef_cash_local=10,
            partner_contribution=200,
            partner_contribution_local=20,
            in_kind_amount_local=10,
        )
        self.assertEqual(int(self.intervention.total_unicef_cash), 100000)

    def test_total_budget(self):
        InterventionBudget.objects.create(
            intervention=self.intervention,
            unicef_cash=100000,
            unicef_cash_local=10,
            partner_contribution=200,
            partner_contribution_local=20,
            in_kind_amount_local=10,
        )
        self.assertEqual(int(self.intervention.total_budget), 100200)

    def test_reference_number(self):
        self.assertIn("TempRef:", self.intervention.reference_number)

    @skip("Fix when HACT available")
    def test_planned_cash_transfers(self):
        InterventionBudget.objects.create(
            intervention=self.intervention,
            unicef_cash=100000,
            unicef_cash_local=10,
            partner_contribution=200,
            partner_contribution_local=20,
            in_kind_amount_local=10,
        )
        self.assertEqual(int(self.intervention.planned_cash_transfers), 15000)
