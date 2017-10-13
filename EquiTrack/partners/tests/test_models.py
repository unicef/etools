import datetime
import json
from unittest import skip
from actstream.models import model_stream

from django.utils import timezone

from EquiTrack.stream_feed.actions import create_snapshot_activity_stream
from EquiTrack.tests.mixins import FastTenantTestCase as TenantTestCase
from EquiTrack.factories import (
    AgreementAmendmentFactory,
    AgreementFactory,
    AssessmentFactory,
    CountryProgrammeFactory,
    InterventionAmendmentFactory,
    InterventionAttachmentFactory,
    InterventionBudgetFactory,
    InterventionFactory,
    InterventionPlannedVisitsFactory,
    PartnerFactory,
    PartnershipFactory,
)

from funds.models import Donor, Grant

from reports.models import (
    CountryProgramme,
    ResultType,
)
from partners import models


def get_date_from_prior_year():
    '''Return a date for which year < the current year'''
    return datetime.date.today() - datetime.timedelta(days=700)


class TestAgreementNumberGeneration(TenantTestCase):
    '''Test that agreements have the expected base and reference numbers for all types of agreements'''

    fixtures = ['initial_data.json']

    def setUp(self):
        self.date = datetime.date.today()
        self.tenant.country_short_code = 'LEBA'
        self.tenant.save()

    def test_reference_number_pca(self):
        '''Thoroughly exercise agreement reference numbers for PCA'''
        # All of the agreements created here are PCAs, so id is the only part of the reference number that varies
        # for this test.
        reference_number_template = 'LEBA/PCA' + str(self.date.year) + '{id}'

        # test basic sequence
        agreement1 = AgreementFactory()
        expected_reference_number = reference_number_template.format(id=agreement1.id)
        self.assertEqual(agreement1.reference_number, expected_reference_number)

        # create amendment
        models.AgreementAmendmentLog.objects.create(
            agreement=agreement1,
            amended_at=self.date,
            status=models.PCA.ACTIVE
        )
        # reference number should be unchanged.
        self.assertEqual(agreement1.reference_number, expected_reference_number)

        # add another agreement
        agreement2 = AgreementFactory()
        expected_reference_number = reference_number_template.format(id=agreement2.id)
        self.assertEqual(agreement2.reference_number, expected_reference_number)

        # agreement numbering remains the same even if previous agreement is deleted
        agreement3 = AgreementFactory()
        expected_reference_number = reference_number_template.format(id=agreement3.id)
        agreement1.delete()
        self.assertEqual(agreement3.reference_number, expected_reference_number)

        # verify that the 'signed_by' date doesn't change the reference number.
        # set signed_by date to a year that is not the current year.
        expected_reference_number = reference_number_template.format(id=agreement2.id)
        agreement2.signed_by_unicef_date = get_date_from_prior_year()
        agreement2.save()
        self.assertEqual(agreement2.reference_number, expected_reference_number)

        # Verify that reference_number is accessible (if a little strange) prior to the first save.
        agreement4 = AgreementFactory.build()
        self.assertEqual(agreement4.reference_number, reference_number_template.format(id=None))

    def test_reference_number_other(self):
        '''Verify simple agreement reference # generation for all agreement types'''
        reference_number_template = 'LEBA/{agreement_type}' + str(self.date.year) + '{id}'
        agreement_types = [agreement_type[0] for agreement_type in models.Agreement.AGREEMENT_TYPES]
        for agreement_type in agreement_types:
            agreement = AgreementFactory(agreement_type=agreement_type)
            expected_reference_number = reference_number_template.format(agreement_type=agreement_type, id=agreement.id)
            self.assertEqual(agreement.reference_number, expected_reference_number)

    def test_base_number_generation(self):
        '''Verify correct values in the .base_number attribute'''
        base_number_template = 'LEBA/PCA' + str(self.date.year) + '{id}'
        agreement = AgreementFactory()

        expected_base_number = base_number_template.format(id=agreement.id)
        self.assertEqual(agreement.base_number, expected_base_number)

        # Ensure that changing the agreement number doesn't change the base number.
        agreement.update_reference_number(amendment_number=42)
        self.assertEqual(agreement.agreement_number, expected_base_number + '-42')
        self.assertEqual(agreement.base_number, expected_base_number)

        # Ensure base_number is OK to access even when the field it depends on is blank.
        agreement.agreement_number = ''
        self.assertEqual(agreement.base_number, '')

    def test_update_reference_number(self):
        '''Exercise Agreement.update_reference_number()'''
        reference_number_template = 'LEBA/PCA' + str(self.date.year) + '{id}'

        agreement = AgreementFactory.build()

        # Prior to saving, base_number and agreement_number are blank.
        self.assertEqual(agreement.base_number, '')
        self.assertEqual(agreement.agreement_number, '')
        self.assertEqual(agreement.reference_number, reference_number_template.format(id=None))

        # Calling save should call update_reference_number(). Before calling save, I have to save the objects with
        # which this agreement has a FK relationship.
        agreement.partner.save()
        agreement.partner_id = agreement.partner.id
        agreement.country_programme.save()
        agreement.country_programme_id = agreement.country_programme.id
        agreement.save()

        # Ensure base_number, agreement_number, and reference_number are what I expect
        expected_reference_number = reference_number_template.format(id=agreement.id)
        self.assertEqual(agreement.base_number, expected_reference_number)
        self.assertEqual(agreement.agreement_number, expected_reference_number)
        self.assertEqual(agreement.reference_number, expected_reference_number)

        # Update ref number and ensure base_number, agreement_number, and reference_number are what I expect
        agreement.update_reference_number(amendment_number=42)
        self.assertEqual(agreement.base_number, expected_reference_number)
        self.assertEqual(agreement.agreement_number, expected_reference_number + '-42')
        self.assertEqual(agreement.reference_number, expected_reference_number)

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
        models.AmendmentLog.objects.create(
            partnership=intervention2,
            amended_at=self.date,
            status=models.PCA.ACTIVE
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
        current_cp = CountryProgramme.objects.create(
            name='Current Country Programme',
            from_date=datetime.date(year, 1, 1),
            to_date=datetime.date(year + 1, 12, 31)
        )
        grant = Grant.objects.create(
            donor=Donor.objects.create(name='Test Donor'),
            name='SM12345678'
        )
        models.InterventionBudget.objects.create(
            intervention=self.intervention,
            partner_contribution=10000,
            unicef_cash=60000,
            in_kind_amount=5000
        )

        tz = timezone.get_default_timezone()

        start = datetime.datetime.combine(current_cp.from_date, datetime.time(0, 0, 1, tzinfo=tz))
        end = current_cp.from_date + datetime.timedelta(days=200)
        end = datetime.datetime.combine(end, datetime.time(23, 59, 59, tzinfo=tz))
        models.FundingCommitment.objects.create(
            start=start,
            end=end,
            grant=grant,
            fr_number='0123456789',
            wbs='Test',
            fc_type='PCA',
            expenditure_amount=40000.00
        )

        start = current_cp.from_date + datetime.timedelta(days=200)
        start = datetime.datetime.combine(start, datetime.time(0, 0, 1, tzinfo=tz))
        end = datetime.datetime.combine(current_cp.to_date, datetime.time(23, 59, 59, tzinfo=tz))
        models.FundingCommitment.objects.create(
            start=start,
            end=end,
            grant=grant,
            fr_number='0123456789',
            wbs='Test',
            fc_type='PCA',
            expenditure_amount=40000.00
        )

    def test_planned_cash_transfers(self):

        models.PartnerOrganization.planned_cash_transfers(self.intervention.agreement.partner)
        hact = self.intervention.agreement.partner.hact_values
        hact = json.loads(hact) if isinstance(hact, str) else hact
        self.assertEqual(hact['planned_cash_transfer'], 60000)


class TestPartnerOrganizationModel(TenantTestCase):
    fixtures = ['initial_data.json']

    def setUp(self):
        self.partner_organization = PartnerFactory(
            name="Partner Org 1",
        )
        year = datetime.date.today().year
        self.cp = CountryProgrammeFactory(
            name="CP 1",
            wbs="0001/A0/01",
            from_date=datetime.date(year - 1, 1, 1),
            to_date=datetime.date(year + 1, 1, 1),
        )
        self.pca_signed1 = AgreementFactory(
            agreement_type=models.Agreement.PCA,
            partner=self.partner_organization,
            signed_by_unicef_date=datetime.date(year - 1, 1, 1),
            signed_by_partner_date=datetime.date(year - 1, 1, 1),
            country_programme=self.cp,
        )
        AgreementFactory(
            agreement_type=models.Agreement.PCA,
            partner=self.partner_organization,
            signed_by_unicef_date=datetime.date(year - 2, 1, 1),
            signed_by_partner_date=datetime.date(year - 2, 1, 1),
            country_programme=self.cp,
        )
        AgreementFactory(
            agreement_type=models.Agreement.PCA,
            partner=self.partner_organization,
            country_programme=self.cp,
            signed_by_unicef_date=None,
            signed_by_partner_date=None,
            status=models.Agreement.DRAFT
        )

    def test_get_last_pca(self):
        pca = self.partner_organization.get_last_pca
        self.assertEqual(pca, self.pca_signed1)

    def test_micro_assessment_needed_high_risk(self):
        year = datetime.date.today().year
        self.partner_organization.type_of_assessment = "High Risk Assumed"
        self.partner_organization.save()
        models.Assessment.objects.create(
            partner=self.partner_organization,
            type="Micro Assessment",
            completed_date=datetime.date(year, 1, 1)
        )
        models.PartnerOrganization.micro_assessment_needed(self.partner_organization)
        self.assertEqual(self.partner_organization.hact_values["micro_assessment_needed"], "Yes")

    def test_micro_assessment_needed_pct_over_100k(self):
        year = datetime.date.today().year
        self.partner_organization.type_of_assessment = "Simplified Checklist"
        self.partner_organization.hact_values["planned_cash_transfer"] = 100001.00
        self.partner_organization.save()
        models.Assessment.objects.create(
            partner=self.partner_organization,
            type="Micro Assessment",
            completed_date=datetime.date(year, 1, 1)
        )
        models.PartnerOrganization.micro_assessment_needed(self.partner_organization)
        self.assertEqual(self.partner_organization.hact_values["micro_assessment_needed"], "Yes")

    def test_micro_assessment_needed_older_than_54m(self):
        self.partner_organization.type_of_assessment = "Micro Assessment"
        self.partner_organization.rating = "low"
        self.partner_organization.hact_values["planned_cash_transfer"] = 10000.00
        self.partner_organization.save()
        models.Assessment.objects.create(
            partner=self.partner_organization,
            type="Micro Assessment",
            completed_date=datetime.date.today() - datetime.timedelta(days=1643)
        )
        models.PartnerOrganization.micro_assessment_needed(self.partner_organization)
        self.assertEqual(self.partner_organization.hact_values["micro_assessment_needed"], "Yes")

    def test_micro_assessment_needed_missing(self):
        self.partner_organization.hact_values["planned_cash_transfer"] = 10000.00
        self.partner_organization.save()
        models.PartnerOrganization.micro_assessment_needed(self.partner_organization)
        self.assertEqual(self.partner_organization.hact_values["micro_assessment_needed"], "Missing")

    def test_micro_assessment_needed_no(self):
        year = datetime.date.today().year
        self.partner_organization.type_of_assessment = "Other"
        self.partner_organization.hact_values["planned_cash_transfer"] = 100000.00
        self.partner_organization.save()
        models.Assessment.objects.create(
            partner=self.partner_organization,
            type="Micro Assessment",
            completed_date=datetime.date(year, 1, 1)
        )
        models.PartnerOrganization.micro_assessment_needed(self.partner_organization)
        self.assertEqual(self.partner_organization.hact_values["micro_assessment_needed"], "No")

    def test_micro_assessment_needed_completed_date(self):
        year = datetime.date.today().year
        self.partner_organization.type_of_assessment = "High Risk Assumed"
        self.partner_organization.save()
        models.Assessment.objects.create(
            partner=self.partner_organization,
            type="Micro Assessment",
            completed_date=datetime.date(year, 1, 1)
        )
        assessment_last = models.Assessment.objects.create(
            partner=self.partner_organization,
            type="Micro Assessment",
            completed_date=datetime.date(year, 2, 1)
        )
        models.PartnerOrganization.micro_assessment_needed(
            self.partner_organization,
            assessment_last
        )
        self.assertEqual(self.partner_organization.hact_values["micro_assessment_needed"], "Yes")

    def test_audit_needed_under_500k(self):
        self.partner_organization.total_ct_cp = 500000.00
        self.partner_organization.save()
        models.PartnerOrganization.audit_needed(self.partner_organization)
        self.assertEqual(self.partner_organization.hact_values['audits_mr'], 0)

    def test_audit_needed_over_500k(self):
        self.partner_organization.total_ct_cp = 500001.00
        self.partner_organization.save()
        models.PartnerOrganization.audit_needed(self.partner_organization)
        self.assertEqual(self.partner_organization.hact_values['audits_mr'], 1)

    def test_audit_needed_extra_assessment_only(self):
        assessment = models.Assessment.objects.create(
            partner=self.partner_organization,
            type="Scheduled Audit report",
            completed_date=datetime.date(datetime.date.today().year, 2, 1)
        )
        self.partner_organization.total_ct_cp = 500001.00
        self.partner_organization.save()
        models.PartnerOrganization.audit_needed(self.partner_organization, assessment)
        self.assertEqual(self.partner_organization.hact_values['audits_mr'], 1)

    def test_audit_done(self):
        models.Assessment.objects.create(
            partner=self.partner_organization,
            type="Scheduled Audit report",
            completed_date=datetime.date(datetime.date.today().year, 1, 1)
        )
        self.partner_organization.total_ct_cp = 500001.00
        self.partner_organization.save()
        models.PartnerOrganization.audit_done(self.partner_organization)
        self.assertEqual(self.partner_organization.hact_values['audits_done'], 1)

    def test_audit_done_zero(self):
        models.PartnerOrganization.audit_done(self.partner_organization)
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

    @skip('Deprecated Functionality')
    def test_planned_cash_transfers_gov(self):
        self.partner_organization.partner_type = "Government"
        self.partner_organization.save()
        CountryProgramme.objects.create(
            name="CP 1",
            wbs="0001/A0/01",
            from_date=datetime.date(datetime.date.today().year - 1, 1, 1),
            to_date=datetime.date(datetime.date.today().year + 1, 1, 1),
        )
        gi = models.GovernmentIntervention.objects.create(
            partner=self.partner_organization,
        )
        rt = ResultType.objects.get(id=1)
        r = models.Result.objects.create(
            result_type=rt,
        )
        models.GovernmentInterventionResult.objects.create(
            intervention=gi,
            result=r,
            year=datetime.date.today().year,
            planned_amount=100000,
        )
        models.GovernmentInterventionResult.objects.create(
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
        agreement = models.Agreement.objects.create(
            agreement_type=models.Agreement.PCA,
            partner=self.partner_organization,
            country_programme=self.cp,
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
        intervention = InterventionFactory(
            agreement=self.pca_signed1,
            status=models.Intervention.ACTIVE
        )
        year = datetime.date.today().year
        InterventionPlannedVisitsFactory(
            intervention=intervention,
            year=year,
            programmatic=3
        )
        InterventionPlannedVisitsFactory(
            intervention=intervention,
            year=year - 1,
            programmatic=2
        )
        self.assertEqual(self.partner_organization.hact_values['planned_visits'], 0)

    def test_planned_visits_non_gov(self):
        self.partner_organization.partner_type = "UN Agency"
        self.partner_organization.status = models.PCA.ACTIVE
        self.partner_organization.save()
        intervention = InterventionFactory(
            agreement=self.pca_signed1,
            status=models.Intervention.ACTIVE
        )
        year = datetime.date.today().year
        InterventionPlannedVisitsFactory(
            intervention=intervention,
            year=year,
            programmatic=3
        )
        InterventionPlannedVisitsFactory(
            intervention=intervention,
            year=year - 1,
            programmatic=2
        )
        self.assertEqual(self.partner_organization.hact_values['planned_visits'], 3)

    def test_planned_visits_non_gov_no_pv_intervention(self):
        self.partner_organization.partner_type = "UN Agency"
        self.partner_organization.status = models.PCA.ACTIVE
        self.partner_organization.save()
        intervention1 = InterventionFactory(
            agreement=self.pca_signed1,
            status=models.Intervention.ACTIVE
        )
        intervention2 = InterventionFactory(
            agreement=self.pca_signed1,
            status=models.Intervention.ACTIVE
        )
        year = datetime.date.today().year
        InterventionPlannedVisitsFactory(
            intervention=intervention1,
            year=year,
            programmatic=3
        )
        InterventionPlannedVisitsFactory(
            intervention=intervention2,
            year=year - 1,
            programmatic=2
        )
        models.PartnerOrganization.planned_visits(
            self.partner_organization
        )
        self.assertEqual(
            self.partner_organization.hact_values['planned_visits'],
            3
        )

    def test_planned_visits_non_gov_with_pv_intervention(self):
        self.partner_organization.partner_type = "UN Agency"
        self.partner_organization.status = models.PCA.ACTIVE
        self.partner_organization.save()
        intervention1 = InterventionFactory(
            agreement=self.pca_signed1,
            status=models.Intervention.ACTIVE
        )
        intervention2 = InterventionFactory(
            agreement=self.pca_signed1,
            status=models.Intervention.ACTIVE
        )
        year = datetime.date.today().year
        pv = InterventionPlannedVisitsFactory(
            intervention=intervention1,
            year=year,
            programmatic=3
        )
        InterventionPlannedVisitsFactory(
            intervention=intervention2,
            year=year - 1,
            programmatic=2
        )
        models.PartnerOrganization.planned_visits(
            self.partner_organization,
            pv
        )
        self.assertEqual(
            self.partner_organization.hact_values['planned_visits'],
            3
        )


class TestAgreementModel(TenantTestCase):
    fixtures = ['initial_data.json']

    def setUp(self):
        self.partner_organization = models.PartnerOrganization.objects.create(
            name="Partner Org 1",
        )
        cp = CountryProgramme.objects.create(
            name="CP 1",
            wbs="0001/A0/01",
            from_date=datetime.date(datetime.date.today().year - 1, 1, 1),
            to_date=datetime.date(datetime.date.today().year + 1, 1, 1),
        )
        self.agreement = models.Agreement.objects.create(
            agreement_type=models.Agreement.PCA,
            partner=self.partner_organization,
            country_programme=cp
        )
        # Trigger created event activity stream
        create_snapshot_activity_stream(
            self.partner_organization, self.agreement, created=True)

    def test_reference_number(self):
        self.assertIn("PCA", self.agreement.reference_number)

    def test_snapshot_activity_stream(self):
        self.agreement.start = datetime.date.today()
        self.agreement.signed_by_unicef_date = datetime.date.today()

        create_snapshot_activity_stream(
            self.partner_organization, self.agreement)
        self.agreement.save()

        # Check if new activity action has been created
        self.assertEqual(model_stream(models.Agreement).count(), 2)

        # Check the previous content
        previous = model_stream(models.Agreement).first().data['previous']
        self.assertNotEqual(previous, {})

        # Check the changes content
        changes = model_stream(models.Agreement).first().data['changes']
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
        self.partner_organization = models.PartnerOrganization.objects.create(
            name="Partner Org 1",
        )
        cp = CountryProgramme.objects.create(
            name="CP 1",
            wbs="0001/A0/01",
            from_date=datetime.date(datetime.date.today().year - 1, 1, 1),
            to_date=datetime.date(datetime.date.today().year + 1, 1, 1),
        )
        agreement = models.Agreement.objects.create(
            agreement_type=models.Agreement.PCA,
            partner=self.partner_organization,
            country_programme=cp,
        )
        self.intervention = models.Intervention.objects.create(
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
        models.InterventionBudget.objects.create(
            intervention=self.intervention,
            unicef_cash=100000,
            unicef_cash_local=10,
            partner_contribution=200,
            partner_contribution_local=20,
            in_kind_amount_local=10,
        )
        self.assertEqual(int(self.intervention.total_unicef_cash), 100000)

    def test_total_budget(self):
        models.InterventionBudget.objects.create(
            intervention=self.intervention,
            unicef_cash=100000,
            unicef_cash_local=10,
            partner_contribution=200,
            partner_contribution_local=20,
            in_kind_amount_local=10,
        )
        self.assertEqual(int(self.intervention.total_budget), 100200)

    def test_year(self):
        '''Exercise the year property'''
        self.assertIsNone(self.intervention.signed_by_unicef_date)
        self.assertEqual(self.intervention.year, self.intervention.created.year)
        self.intervention.signed_by_unicef_date = get_date_from_prior_year()
        self.assertEqual(self.intervention.year, self.intervention.signed_by_unicef_date.year)

    def test_reference_number(self):
        '''Exercise the reference number property'''
        expected_reference_number = self.intervention.agreement.base_number + '/' + self.intervention.document_type
        expected_reference_number += str(self.intervention.created.year) + str(self.intervention.id)
        self.assertEqual(self.intervention.reference_number, expected_reference_number)

        self.intervention.signed_by_unicef_date = get_date_from_prior_year()

        expected_reference_number = self.intervention.agreement.base_number + '/' + self.intervention.document_type
        expected_reference_number += str(self.intervention.signed_by_unicef_date.year) + str(self.intervention.id)
        self.assertEqual(self.intervention.reference_number, expected_reference_number)

    @skip("Fix when HACT available")
    def test_planned_cash_transfers(self):
        models.InterventionBudget.objects.create(
            intervention=self.intervention,
            unicef_cash=100000,
            unicef_cash_local=10,
            partner_contribution=200,
            partner_contribution_local=20,
            in_kind_amount_local=10,
        )
        self.assertEqual(int(self.intervention.planned_cash_transfers), 15000)


class TestGetFilePaths(TenantTestCase):
    def test_get_agreement_path(self):
        partner = PartnerFactory()
        agreement = models.Agreement(
            agreement_number="123",
            partner=partner,
        )
        p = models.get_agreement_path(agreement, "test.pdf")
        self.assertTrue(p.endswith("/agreements/123/test.pdf"))

    def test_get_assessment_path(self):
        partner = PartnerFactory()
        assessment = AssessmentFactory(
            partner=partner,
        )
        p = models.get_assesment_path(assessment, "test.pdf")
        self.assertTrue(
            p.endswith("/assesments/{}/test.pdf".format(assessment.pk))
        )

    def test_get_intervention_path(self):
        agreement = AgreementFactory()
        intervention = InterventionFactory(
            agreement=agreement
        )
        p = models.get_intervention_file_path(intervention, "test.pdf")
        self.assertTrue(
            p.endswith("/agreements/{}/interventions/{}/test.pdf".format(
                agreement.pk,
                intervention.pk
            ))
        )

    def test_get_prc_intervention_path(self):
        agreement = AgreementFactory()
        intervention = InterventionFactory(
            agreement=agreement
        )
        p = models.get_prc_intervention_file_path(intervention, "test.pdf")
        self.assertTrue(
            p.endswith(
                "/agreements/{}/interventions/{}/prc/test.pdf".format(
                    agreement.pk,
                    intervention.pk
                )
            )
        )

    def test_get_intervention_amendment_file_path(self):
        agreement = AgreementFactory()
        intervention = InterventionFactory(
            agreement=agreement
        )
        amendment = InterventionAmendmentFactory(
            intervention=intervention
        )
        p = models.get_intervention_amendment_file_path(amendment, "test.pdf")
        self.assertTrue(
            p.endswith("/agreements/{}/interventions/{}/amendments/{}/test.pdf".format(
                agreement.pk,
                intervention.pk,
                amendment.pk
            ))
        )

    def test_get_intervention_attachments_file_path(self):
        agreement = AgreementFactory()
        intervention = InterventionFactory(
            agreement=agreement
        )
        attachment = InterventionAttachmentFactory(
            intervention=intervention
        )
        p = models.get_intervention_attachments_file_path(
            attachment,
            "test.pdf"
        )
        self.assertTrue(
            p.endswith("/agreements/{}/interventions/{}/attachments/{}/test.pdf".format(
                agreement.pk,
                intervention.pk,
                attachment.pk
            ))
        )

    def test_get_agreement_amd_file_path(self):
        agreement = AgreementFactory()
        amendment = AgreementAmendmentFactory(
            agreement=agreement,
        )
        p = models.get_agreement_amd_file_path(amendment, "test.pdf")
        self.assertTrue(
            p.endswith("/agreements/{}/amendments/{}/test.pdf".format(
                agreement.base_number,
                amendment.number,
            ))
        )


class TestWorkspaceFileType(TenantTestCase):
    def test_unicode(self):
        w = models.WorkspaceFileType(name="Test")
        self.assertEqual(unicode(w), u"Test")


class TestPartnerOrganization(TenantTestCase):
    def test_unicode(self):
        p = models.PartnerOrganization(name="Test Partner Org")
        self.assertEqual(unicode(p), "Test Partner Org")

    def test_save_exception(self):
        p = models.PartnerOrganization(name="Test", hact_values="wrong")
        with self.assertRaises(ValueError):
            p.save()

    def test_save(self):
        p = models.PartnerOrganization(
            name="Test",
            hact_values={'all': 'good'}
        )
        p.save()
        self.assertIsNotNone(p.pk)

    def test_save_hact_is_string(self):
        p = models.PartnerOrganization(
            name="Test",
            hact_values='{"all": "good"}'
        )
        self.assertTrue(isinstance(p.hact_values, str))
        p.save()
        self.assertIsNotNone(p.pk)
        self.assertTrue(isinstance(p.hact_values, str))
        self.assertEqual(p.hact_values, '{"all": "good"}')
