import copy
import datetime
import json

from unittest import skip
from mock import patch, Mock
from django.utils import timezone

from EquiTrack.factories import (
    AgreementAmendmentFactory,
    AgreementFactory,
    AppliedIndicatorFactory,
    AssessmentFactory,
    CountryProgrammeFactory,
    CurrencyFactory,
    DonorFactory,
    FundsReservationHeaderFactory,
    GovernmentInterventionFactory,
    GrantFactory,
    InterventionAmendmentFactory,
    InterventionAttachmentFactory,
    InterventionBudgetFactory,
    InterventionFactory,
    InterventionPlannedVisitsFactory,
    InterventionReportingPeriodFactory,
    InterventionResultLinkFactory,
    InterventionSectorLocationLinkFactory,
    LocationFactory,
    LowerResultFactory,
    PartnerFactory,
    PartnerStaffFactory,
    ResultFactory,
    SectorFactory,
    TravelFactory,
    TravelActivityFactory,
    UserFactory,
)
from EquiTrack.tests.mixins import FastTenantTestCase as TenantTestCase

from reports.models import ResultType
from partners import models
from t2f.models import Travel, TravelType


def get_date_from_prior_year():
    '''Return a date for which year < the current year'''
    return datetime.date.today() - datetime.timedelta(days=700)


class TestGetCurrencyNameOrDefault(TenantTestCase):
    def test_none(self):
        self.assertIsNone(models._get_currency_name_or_default(False))

    def test_no_currency(self):
        budget = InterventionBudgetFactory(
            currency=None
        )
        self.assertIsNone(models._get_currency_name_or_default(budget))

    def test_currency(self):
        currency = CurrencyFactory(code="USD")
        budget = InterventionBudgetFactory(
            currency=currency
        )
        self.assertEqual(models._get_currency_name_or_default(budget), "USD")


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
        AgreementAmendmentFactory(agreement=agreement1)
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


class TestHACTCalculations(TenantTestCase):
    fixtures = ['initial_data.json']

    def setUp(self):
        year = datetime.date.today().year
        self.intervention = InterventionFactory(
            status=u'active'
        )
        current_cp = CountryProgrammeFactory(
            name='Current Country Programme',
            from_date=datetime.date(year, 1, 1),
            to_date=datetime.date(year + 1, 12, 31)
        )
        grant = GrantFactory(
            donor=DonorFactory(name='Test Donor'),
            name='SM12345678'
        )
        InterventionBudgetFactory(
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
            status=models.Agreement.DRAFT
        )
        AgreementFactory(
            agreement_type=models.Agreement.PCA,
            partner=self.partner_organization,
            signed_by_unicef_date=datetime.date(year - 2, 1, 1),
            signed_by_partner_date=datetime.date(year - 2, 1, 1),
            country_programme=self.cp,
            status=models.Agreement.DRAFT
        )
        AgreementFactory(
            agreement_type=models.Agreement.PCA,
            partner=self.partner_organization,
            country_programme=self.cp,
            signed_by_unicef_date=None,
            signed_by_partner_date=None,
            status=models.Agreement.DRAFT
        )

    def test_latest_assessment(self):
        date = datetime.date(2001, 1, 1)
        assessment_type = "Micro Assessment"
        AssessmentFactory(
            partner=self.partner_organization,
            type=assessment_type,
            completed_date=date + datetime.timedelta(days=1)
        )
        AssessmentFactory(
            partner=self.partner_organization,
            type=assessment_type,
            completed_date=date + datetime.timedelta(days=2)
        )
        assessment = AssessmentFactory(
            partner=self.partner_organization,
            type=assessment_type,
            completed_date=date + datetime.timedelta(days=3)
        )
        self.assertEqual(
            self.partner_organization.latest_assessment(assessment_type),
            assessment
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
        self.partner_organization.partner_type = models.PartnerType.GOVERNMENT
        self.partner_organization.save()
        CountryProgrammeFactory(
            name="CP 1",
            wbs="0001/A0/01",
            from_date=datetime.date(datetime.date.today().year - 1, 1, 1),
            to_date=datetime.date(datetime.date.today().year + 1, 1, 1),
        )
        gi = GovernmentInterventionFactory(
            partner=self.partner_organization,
        )
        rt = ResultType.objects.get(id=1)
        r = ResultFactory(
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
        self.partner_organization.partner_type = models.PartnerType.UN_AGENCY
        self.partner_organization.save()
        agreement = AgreementFactory(
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
        self.partner_organization.partner_type = models.PartnerType.GOVERNMENT
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
        self.partner_organization.partner_type = models.PartnerType.UN_AGENCY
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
        self.partner_organization.partner_type = models.PartnerType.UN_AGENCY
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
        self.partner_organization.partner_type = models.PartnerType.UN_AGENCY
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

    def test_programmatic_visits_update_one(self):
        self.assertEqual(
            self.partner_organization.hact_values["programmatic_visits"],
            0
        )
        models.PartnerOrganization.programmatic_visits(
            self.partner_organization,
            update_one=True
        )
        self.assertEqual(
            self.partner_organization.hact_values["programmatic_visits"],
            1
        )

    def test_programmatic_visits_update_travel_activity(self):
        self.assertEqual(
            self.partner_organization.hact_values["programmatic_visits"],
            0
        )
        traveller = UserFactory()
        travel = TravelFactory(
            traveler=traveller,
            status=Travel.COMPLETED,
            completed_at=datetime.datetime.now()
        )
        TravelActivityFactory(
            travels=[travel],
            primary_traveler=traveller,
            travel_type=TravelType.PROGRAMME_MONITORING,
            partner=self.partner_organization,
        )
        models.PartnerOrganization.programmatic_visits(
            self.partner_organization,
        )
        self.assertEqual(
            self.partner_organization.hact_values["programmatic_visits"],
            1
        )

    def test_spot_checks_update_one(self):
        self.assertEqual(
            self.partner_organization.hact_values["spot_checks"],
            0
        )
        models.PartnerOrganization.spot_checks(
            self.partner_organization,
            update_one=True,
        )
        self.assertEqual(
            self.partner_organization.hact_values["spot_checks"],
            1
        )

    def test_spot_checks_update_travel_activity(self):
        self.assertEqual(
            self.partner_organization.hact_values["spot_checks"],
            0
        )
        traveller = UserFactory()
        travel = TravelFactory(
            traveler=traveller,
            status=Travel.COMPLETED,
            completed_at=datetime.datetime.now()
        )
        TravelActivityFactory(
            travels=[travel],
            primary_traveler=traveller,
            travel_type=TravelType.SPOT_CHECK,
            partner=self.partner_organization,
        )
        models.PartnerOrganization.spot_checks(
            self.partner_organization,
        )
        self.assertEqual(
            self.partner_organization.hact_values["spot_checks"],
            1
        )

    def test_follow_up_flags(self):
        """Test that follow_up_flags method resets the hact_value
        'follow_up_flags' to 0
        """
        self.partner_organization.hact_values["follow_up_flags"] = 1
        self.partner_organization.save()
        self.assertEqual(
            self.partner_organization.hact_values["follow_up_flags"],
            1
        )
        models.PartnerOrganization.follow_up_flags(self.partner_organization)
        partner_update = models.PartnerOrganization.objects.get(
            pk=self.partner_organization.pk
        )
        self.assertEqual(partner_update.hact_values["follow_up_flags"], 0)


class TestAgreementModel(TenantTestCase):
    fixtures = ['initial_data.json']

    def setUp(self):
        self.partner_organization = models.PartnerOrganization.objects.create(
            name="Partner Org 1",
        )
        cp = CountryProgrammeFactory(
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

    def test_reference_number(self):
        self.assertIn("PCA", self.agreement.reference_number)


class TestInterventionModel(TenantTestCase):
    fixtures = ['initial_data.json']

    def setUp(self):
        self.partner_organization = PartnerFactory(name="Partner Org 1")
        cp = CountryProgrammeFactory(
            name="CP 1",
            wbs="0001/A0/01",
            from_date=datetime.date(datetime.date.today().year - 1, 1, 1),
            to_date=datetime.date(datetime.date.today().year + 1, 1, 1),
        )
        self.agreement = AgreementFactory(
            agreement_type=models.Agreement.PCA,
            partner=self.partner_organization,
            country_programme=cp,
        )
        self.intervention = InterventionFactory(
            title="Intervention 1",
            agreement=self.agreement,
            submission_date=datetime.date(datetime.date.today().year, 1, 1),
        )

    def test_unicode(self):
        number = self.intervention.number
        self.assertEqual(unicode(self.intervention), number)

    def test_permission_structure(self):
        permissions = models.Intervention.permission_structure()
        self.assertTrue(isinstance(permissions, dict))
        self.assertEqual(permissions["amendments"], {
            'edit': {
                'true': [
                    {'status': 'draft', 'group': 'Partnership Manager', 'condition': ''},
                    {'status': 'signed', 'group': 'Partnership Manager', 'condition': ''},
                    {'status': 'active', 'group': 'Partnership Manager', 'condition': ''},
                    {'status': 'draft', 'group': 'Partnership Manager', 'condition': ''},
                    {'status': 'signed', 'group': 'Partnership Manager', 'condition': ''},
                    {'status': 'active', 'group': 'Partnership Manager', 'condition': ''}
                ]
            }
        })

    def test_days_from_submission_to_signed(self):
        intervention = InterventionFactory(
            submission_date=datetime.date(2001, 1, 1),
            signed_by_partner_date=datetime.date(2001, 1, 3),
            signed_by_unicef_date=datetime.date(2001, 1, 3),
        )
        self.assertEqual(intervention.days_from_submission_to_signed, 2)

    def test_days_from_submission_to_signed_no_submission_date(self):
        intervention = InterventionFactory(
            agreement=self.agreement,
            submission_date=None
        )
        self.assertIsNone(intervention.submission_date)
        res = intervention.days_from_submission_to_signed
        self.assertEqual(res, "Not Submitted")

    def test_days_from_submission_to_signed_not_signed_by_unicef(self):
        self.assertIsNotNone(self.intervention.submission_date)
        self.assertIsNone(self.intervention.signed_by_unicef_date)
        res = self.intervention.days_from_submission_to_signed
        self.assertEqual(res, "Not fully signed")

    def test_days_from_submission_to_signed_not_signed_by_partner(self):
        self.intervention.signed_by_unicef_date = datetime.date.today()
        self.intervention.save()
        self.assertIsNotNone(self.intervention.submission_date)
        self.assertIsNotNone(self.intervention.signed_by_unicef_date)
        self.assertIsNone(self.intervention.signed_by_partner_date)
        res = self.intervention.days_from_submission_to_signed
        self.assertEqual(res, "Not fully signed")

    def test_submitted_to_prc_submission_date_prc(self):
        self.intervention.submission_date_prc = datetime.date.today()
        self.intervention.save()
        self.assertTrue(self.intervention.submitted_to_prc)

    def test_submitted_to_prc_review_date_prc(self):
        self.intervention.review_date_prc = datetime.date.today()
        self.intervention.save()
        self.assertTrue(self.intervention.submitted_to_prc)

    def test_submitted_to_prc_review_document(self):
        self.intervention.prc_review_document = "test.pdf"
        self.intervention.save()
        self.assertTrue(self.intervention.submitted_to_prc)

    def test_submitted_to_prc_false(self):
        self.intervention.submission_date_prc = None
        self.intervention.save()
        self.assertIsNone(self.intervention.submission_date_prc)
        self.assertFalse(self.intervention.submitted_to_prc)

    def test_days_from_review_to_signed(self):
        intervention = InterventionFactory(
            review_date_prc=datetime.date(2001, 1, 1),
            signed_by_partner_date=datetime.date(2001, 1, 3),
            signed_by_unicef_date=datetime.date(2001, 1, 3),
        )
        self.assertEqual(intervention.days_from_review_to_signed, 2)

    def test_days_from_review_to_signed_no_review_date_prc(self):
        self.assertIsNone(self.intervention.review_date_prc)
        res = self.intervention.days_from_review_to_signed
        self.assertEqual(res, "Not Reviewed")

    def test_days_from_review_to_signed_not_signed_by_unicef(self):
        self.intervention.review_date_prc = datetime.date.today()
        self.intervention.save()
        self.assertIsNotNone(self.intervention.review_date_prc)
        self.assertIsNone(self.intervention.signed_by_unicef_date)
        res = self.intervention.days_from_review_to_signed
        self.assertEqual(res, "Not fully signed")

    def test_days_from_review_to_signed_not_signed_by_partner(self):
        self.intervention.review_date_prc = datetime.date.today()
        self.intervention.signed_by_unicef_date = datetime.date.today()
        self.intervention.save()
        self.assertIsNotNone(self.intervention.review_date_prc)
        self.assertIsNotNone(self.intervention.signed_by_unicef_date)
        self.assertIsNone(self.intervention.signed_by_partner_date)
        res = self.intervention.days_from_review_to_signed
        self.assertEqual(res, "Not fully signed")

    def test_sector_names(self):
        sector_1 = SectorFactory(name="ABC")
        sector_2 = SectorFactory(name="CBA")
        intervention = InterventionFactory()
        InterventionSectorLocationLinkFactory(
            intervention=intervention,
            sector=sector_1,
        )
        InterventionSectorLocationLinkFactory(
            intervention=intervention,
            sector=sector_2,
        )
        self.assertEqual(intervention.sector_names, "ABC, CBA")

    def test_sector_names_empty(self):
        self.assertEqual(self.intervention.sector_names, "")

    def test_default_budget_currency(self):
        currency = CurrencyFactory(code="USD")
        intervention = InterventionFactory()
        InterventionBudgetFactory(
            currency=currency,
            intervention=intervention
        )
        self.assertEqual(intervention.default_budget_currency, "USD")

    def test_fr_currency_empty(self):
        self.assertIsNone(self.intervention.fr_currency)

    def test_fr_currency(self):
        intervention = InterventionFactory()
        FundsReservationHeaderFactory(
            currency="USD",
            intervention=intervention,
        )
        self.assertEqual(intervention.fr_currency, "USD")

    def test_duration(self):
        self.intervention.start_date = datetime.date(datetime.date.today().year - 1, 1, 1)
        self.intervention.end_date = datetime.date(datetime.date.today().year + 1, 1, 1)
        # self.assertEqual(self.intervention.duration, 24)

    def test_total_no_intervention(self):
        self.assertEqual(int(self.intervention.total_unicef_cash), 0)
        self.assertEqual(int(self.intervention.total_partner_contribution), 0)
        self.assertEqual(int(self.intervention.total_budget), 0)
        self.assertEqual(int(self.intervention.total_unicef_budget), 0)
        self.assertEqual(int(self.intervention.total_partner_contribution_local), 0)
        self.assertEqual(int(self.intervention.total_unicef_cash_local), 0)
        self.assertEqual(int(self.intervention.total_budget_local), 0)

    def test_total_unicef_cash(self):
        InterventionBudgetFactory(
            intervention=self.intervention,
            unicef_cash=100000,
            unicef_cash_local=10,
            partner_contribution=200,
            partner_contribution_local=20,
            in_kind_amount_local=10,
        )
        self.assertEqual(int(self.intervention.total_unicef_cash), 100000)

    def test_total_partner_contribution(self):
        InterventionBudgetFactory(
            intervention=self.intervention,
            unicef_cash=100000,
            unicef_cash_local=10,
            partner_contribution=200,
            partner_contribution_local=20,
            in_kind_amount_local=10,
        )
        self.assertEqual(int(self.intervention.total_partner_contribution), 200)

    def test_total_budget(self):
        InterventionBudgetFactory(
            intervention=self.intervention,
            unicef_cash=100000,
            unicef_cash_local=10,
            partner_contribution=200,
            partner_contribution_local=20,
            in_kind_amount_local=10,
        )
        self.assertEqual(int(self.intervention.total_budget), 100210)

    def test_total_in_kind_amount(self):
        InterventionBudgetFactory(
            intervention=self.intervention,
            unicef_cash=100000,
            unicef_cash_local=10,
            partner_contribution=200,
            in_kind_amount=3300,
            in_kind_amount_local=10,
        )
        self.assertEqual(int(self.intervention.total_in_kind_amount), 3300)

    def test_total_unicef_budget(self):
        InterventionBudgetFactory(
            intervention=self.intervention,
            unicef_cash=100000,
            unicef_cash_local=10,
            partner_contribution=200,
            in_kind_amount=2000,
            in_kind_amount_local=10,
        )
        self.assertEqual(int(self.intervention.total_unicef_budget), 102000)

    def test_total_partner_contribution_local(self):
        InterventionBudgetFactory(
            intervention=self.intervention,
            unicef_cash=100000,
            unicef_cash_local=10,
            partner_contribution_local=7000,
            in_kind_amount=2000,
            in_kind_amount_local=10,
        )
        self.assertEqual(int(self.intervention.total_partner_contribution_local), 7000)

    def test_total_unicef_cash_local(self):
        InterventionBudgetFactory(
            intervention=self.intervention,
            unicef_cash=100000,
            unicef_cash_local=10,
            partner_contribution_local=7000,
            in_kind_amount=2000,
            in_kind_amount_local=10,
        )
        self.assertEqual(int(self.intervention.total_unicef_cash_local), 10)

    def test_total_budget_local(self):
        InterventionBudgetFactory(
            intervention=self.intervention,
            unicef_cash=100000,
            unicef_cash_local=10,
            partner_contribution_local=7000,
            in_kind_amount=2000,
            in_kind_amount_local=3000,
        )
        self.assertEqual(int(self.intervention.total_budget_local), 3000)

    def test_year(self):
        '''Exercise the year property'''
        self.assertIsNone(self.intervention.signed_by_unicef_date)
        self.assertEqual(self.intervention.year, self.intervention.created.year)
        self.intervention.signed_by_unicef_date = get_date_from_prior_year()
        self.assertEqual(self.intervention.year, self.intervention.signed_by_unicef_date.year)

    def test_year_no_pk(self):
        i = models.Intervention()
        self.assertEqual(i.year, datetime.date.today().year)

    def test_reference_number(self):
        '''Exercise the reference number property'''
        expected_reference_number = self.intervention.agreement.base_number + '/' + self.intervention.document_type
        expected_reference_number += str(self.intervention.created.year) + str(self.intervention.id)
        self.assertEqual(self.intervention.reference_number, expected_reference_number)

        self.intervention.signed_by_unicef_date = get_date_from_prior_year()

        expected_reference_number = self.intervention.agreement.base_number + '/' + self.intervention.document_type
        expected_reference_number += str(self.intervention.signed_by_unicef_date.year) + str(self.intervention.id)
        self.assertEqual(self.intervention.reference_number, expected_reference_number)

    def test_all_lower_results_empty(self):
        self.assertEqual(self.intervention.all_lower_results, [])

    def test_all_lower_results(self):
        intervention = InterventionFactory()
        link = InterventionResultLinkFactory(
            intervention=intervention,
        )
        lower_result_1 = LowerResultFactory(result_link=link)
        lower_result_2 = LowerResultFactory(result_link=link)
        self.assertItemsEqual(intervention.all_lower_results, [
            lower_result_1,
            lower_result_2,
        ])

    def test_intervention_locations_empty(self):
        self.assertFalse(self.intervention.intervention_locations)

    def test_intervention_locations(self):
        intervention = InterventionFactory()
        link = InterventionResultLinkFactory(
            intervention=intervention,
        )
        lower_result_1 = LowerResultFactory(result_link=link)
        location_1 = LocationFactory()
        applied_indicator_1 = AppliedIndicatorFactory(
            lower_result=lower_result_1
        )
        applied_indicator_1.locations.add(location_1)
        lower_result_2 = LowerResultFactory(result_link=link)
        location_2 = LocationFactory()
        applied_indicator_2 = AppliedIndicatorFactory(
            lower_result=lower_result_2
        )
        applied_indicator_2.locations.add(location_2)
        self.assertItemsEqual(intervention.intervention_locations, [
            location_1,
            location_2,
        ])

    def test_intervention_clusters_empty(self):
        self.assertFalse(self.intervention.intervention_clusters)

    def test_intervention_clusters(self):
        intervention = InterventionFactory()
        link = InterventionResultLinkFactory(
            intervention=intervention,
        )
        lower_result_1 = LowerResultFactory(result_link=link)
        AppliedIndicatorFactory(
            lower_result=lower_result_1,
            cluster_name="Title 1",
        )
        lower_result_2 = LowerResultFactory(result_link=link)
        AppliedIndicatorFactory(
            lower_result=lower_result_2,
            cluster_name="Title 2",
        )
        AppliedIndicatorFactory(
            lower_result=lower_result_2,
            cluster_name=None,
        )
        AppliedIndicatorFactory(lower_result=lower_result_2)
        self.assertItemsEqual(intervention.intervention_clusters, [
            "Title 1",
            "Title 2",
        ])

    def validate_total_frs(
            self,
            frs,
            frs_amt=0,
            ot_amt=0,
            int_amt=0,
            amt=0,
            start=None,
            end=None,
    ):
        self.assertEqual(frs['total_frs_amt'], frs_amt)
        self.assertEqual(frs['total_outstanding_amt'], ot_amt)
        self.assertEqual(frs['total_intervention_amt'], int_amt)
        self.assertEqual(frs['total_actual_amt'], amt)
        self.assertEqual(frs['earliest_start_date'], start)
        self.assertEqual(frs['latest_end_date'], end)

    def test_total_frs_empty(self):
        """Ensure that we handle an empty queryset"""
        self.validate_total_frs(self.intervention.total_frs)

    def test_total_frs_single(self):
        """Ensure that values are set correctly"""
        intervention = InterventionFactory()
        FundsReservationHeaderFactory(
            intervention=intervention,
            total_amt=10.00,
            outstanding_amt=20.00,
            intervention_amt=30.00,
            actual_amt=40.00,
            start_date=datetime.date(2001, 1, 1),
            end_date=datetime.date(2002, 1, 1),
        )
        self.validate_total_frs(
            intervention.total_frs,
            10.00,
            20.00,
            30.00,
            40.00,
            datetime.date(2001, 1, 1),
            datetime.date(2002, 1, 1),
        )

    def test_total_frs_earliest_latest(self):
        """Ensure values are updated correctly

        - amounts are added up
        - start date is the earliest
        - end date is the latest
        """
        intervention = InterventionFactory()
        FundsReservationHeaderFactory(
            intervention=intervention,
            total_amt=10.00,
            outstanding_amt=20.00,
            intervention_amt=30.00,
            actual_amt=40.00,
            start_date=datetime.date(2010, 1, 1),
            end_date=datetime.date(2002, 1, 1),
        )
        FundsReservationHeaderFactory(
            intervention=intervention,
            total_amt=10.00,
            outstanding_amt=20.00,
            intervention_amt=30.00,
            actual_amt=40.00,
            start_date=datetime.date(2001, 1, 1),
            end_date=datetime.date(2020, 1, 1),
        )
        FundsReservationHeaderFactory(
            intervention=intervention,
            total_amt=10.00,
            outstanding_amt=20.00,
            intervention_amt=30.00,
            actual_amt=40.00,
            start_date=datetime.date(2005, 1, 1),
            end_date=datetime.date(2010, 1, 1),
        )
        self.validate_total_frs(
            intervention.total_frs,
            10.00*3,
            20.00*3,
            30.00*3,
            40.00*3,
            datetime.date(2001, 1, 1),
            datetime.date(2020, 1, 1),
        )

    def test_update_ssfa_properties_dates_differ(self):
        """If document type is SSFA and start/end date do not match
        agreement start/end date then update agreement start/end
        and save
        """
        agreement = AgreementFactory(
            agreement_type=models.Agreement.MOU,
            start=datetime.date(2001, 1, 6),
            end=datetime.date(2001, 2, 7),
        )
        self.assertEqual(agreement.start, datetime.date(2001, 1, 6))
        self.assertEqual(agreement.end, datetime.date(2001, 2, 7))
        intervention = InterventionFactory(
            document_type=models.Intervention.SSFA,
            agreement=agreement,
            start=datetime.date(2001, 1, 1),
            end=datetime.date(2001, 2, 1),
        )
        self.assertEqual(intervention.start, agreement.start)
        self.assertEqual(intervention.end, agreement.end)

    def test_update_ssfa_properties_signed(self):
        """If status is signed and agreement status is not signed
        update agreement status to signed and save
        """
        for status in [models.Intervention.SIGNED, models.Intervention.ACTIVE]:
            agreement = AgreementFactory(
                status=models.Agreement.DRAFT,
            )
            self.assertEqual(agreement.status, models.Agreement.DRAFT)
            intervention = InterventionFactory(
                document_type=models.Intervention.SSFA,
                agreement=agreement,
                start=datetime.date(2001, 1, 1),
                end=datetime.date(2001, 2, 1),
                status=status
            )
            self.assertEqual(intervention.status, status)
            self.assertEqual(agreement.status, models.Agreement.SIGNED)

    def test_update_ssfa_properties_active(self):
        """If status is active and agreement status is not signed
        update agreement status to signed and save
        """
        agreement = AgreementFactory(
            status=models.Agreement.DRAFT,
        )
        self.assertEqual(agreement.status, models.Agreement.DRAFT)
        intervention = InterventionFactory(
            document_type=models.Intervention.SSFA,
            agreement=agreement,
            start=datetime.date(2001, 1, 1),
            end=datetime.date(2001, 2, 1),
            status=models.Intervention.ACTIVE
        )
        self.assertEqual(intervention.status, models.Intervention.ACTIVE)
        intervention.update_ssfa_properties()
        agreement_update = models.Agreement.objects.get(pk=agreement.pk)
        self.assertEqual(agreement_update.status, models.Agreement.SIGNED)

    def test_update_ssfa_properties_complete(self):
        """If status is in completed status and agreement status is not
        update agreement status to match and save
        """
        for status in [
                models.Intervention.ENDED,
                models.Intervention.SUSPENDED,
                models.Intervention.TERMINATED
        ]:
            agreement = AgreementFactory(
                status=models.Agreement.DRAFT,
            )
            self.assertEqual(agreement.status, models.Agreement.DRAFT)
            intervention = InterventionFactory(
                document_type=models.Intervention.SSFA,
                agreement=agreement,
                start=datetime.date(2001, 1, 1),
                end=datetime.date(2001, 2, 1),
                status=status
            )
            self.assertEqual(intervention.status, status)
            self.assertEqual(agreement.status, status)

    def test_update_ssfa_properties_closed(self):
        """If status is close and agreement status is not ended
        update agreement status and save
        """
        agreement = AgreementFactory(
            status=models.Agreement.DRAFT,
        )
        self.assertEqual(agreement.status, models.Agreement.DRAFT)
        intervention = InterventionFactory(
            document_type=models.Intervention.SSFA,
            agreement=agreement,
            start=datetime.date(2001, 1, 1),
            end=datetime.date(2001, 2, 1),
            status=models.Intervention.CLOSED
        )
        self.assertEqual(intervention.status, models.Intervention.CLOSED)
        self.assertEqual(agreement.status, models.Agreement.ENDED)


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


class TestPartnerStaffMember(TenantTestCase):
    def test_unicode(self):
        partner = models.PartnerOrganization(name="Partner")
        staff = models.PartnerStaffMember(
            first_name="First",
            last_name="Last",
            partner=partner
        )
        self.assertEqual(unicode(staff), "First Last (Partner)")

    def test_save_update_deactivate(self):
        partner = PartnerFactory()
        staff = PartnerStaffFactory(
            partner=partner,
        )
        self.assertTrue(staff.active)
        mock_send = Mock()
        with patch("partners.models.pre_delete.send", mock_send):
            staff.active = False
            staff.save()
        self.assertEqual(mock_send.call_count, 1)

    def test_save_update_reactivate(self):
        partner = PartnerFactory()
        staff = PartnerStaffFactory(
            partner=partner,
            active=False,
        )
        self.assertFalse(staff.active)
        mock_send = Mock()
        with patch("partners.models.post_save.send", mock_send):
            staff.active = True
            staff.save()
        self.assertEqual(mock_send.call_count, 2)


class TestAssessment(TenantTestCase):
    def test_unicode_not_completed(self):
        partner = models.PartnerOrganization(name="Partner")
        a = models.Assessment(
            partner=partner,
            type="Type",
            rating="Rating",
        )
        self.assertEqual(unicode(a), "Type: Partner Rating NOT COMPLETED")

    def test_unicode_completed(self):
        partner = models.PartnerOrganization(name="Partner")
        a = models.Assessment(
            partner=partner,
            type="Type",
            rating="Rating",
            completed_date=datetime.date(2001, 1, 1)
        )
        self.assertEqual(unicode(a), "Type: Partner Rating 01-01-2001")

    def test_save_update_micro_assessment(self):
        partner = PartnerFactory(
            rating=models.Assessment.LOW,
            type_of_assessment="Micro Assessment",
        )
        assessment = AssessmentFactory(
            partner=partner,
            type="Micro Assessment",
            completed_date=datetime.date(2001, 1, 1)
        )
        self.assertEqual(partner.hact_values["micro_assessment_needed"], "Yes")
        assessment.completed_date = datetime.date.today()
        assessment.save()
        partner_updated = models.PartnerOrganization.objects.get(pk=partner.pk)
        self.assertEqual(
            partner_updated.hact_values["micro_assessment_needed"],
            "No"
        )

    def test_save_update_scheduled_audit_report(self):
        partner = PartnerFactory(
            rating=models.Assessment.LOW,
            type_of_assessment="Micro Assessment",
        )
        assessment = AssessmentFactory(
            partner=partner,
            type="Micro Assessment",
            completed_date=datetime.date(2001, 1, 1)
        )
        self.assertEqual(partner.hact_values["audits_done"], 0)
        assessment.type = "Scheduled Audit report"
        assessment.save()
        self.assertEqual(partner.hact_values["audits_done"], 1)


class TestAgreement(TenantTestCase):
    def test_unicode(self):
        partner = models.PartnerOrganization(name="Partner")
        agreement = models.Agreement(
            partner=partner,
            agreement_type=models.Agreement.DRAFT,
        )
        self.assertEqual(unicode(agreement), "draft for Partner ( - )")

    def test_unicode_dates(self):
        partner = models.PartnerOrganization(name="Partner")
        agreement = models.Agreement(
            partner=partner,
            agreement_type=models.Agreement.DRAFT,
            start=datetime.date(2001, 1, 1),
            end=datetime.date(2002, 1, 1),
        )
        self.assertEqual(
            unicode(agreement),
            "draft for Partner (01-01-2001 - 01-01-2002)"
        )

    def test_permission_structure(self):
        permissions = models.Agreement.permission_structure()
        self.assertTrue(isinstance(permissions, dict))
        self.assertEqual(permissions["amendments"], {
            'edit': {
                'true': [{
                        'status': 'signed',
                        'group': 'Partnership Manager',
                        'condition': 'is type PCA or MOU'
                    }]
            }
        })

    def test_year_signed_by_unicef_date(self):
        agreement = AgreementFactory()
        self.assertIsNotNone(agreement.signed_by_unicef_date)
        self.assertEqual(agreement.year, agreement.signed_by_unicef_date.year)

    def test_year_created(self):
        agreement = AgreementFactory(
            signed_by_unicef_date=None
        )
        self.assertIsNone(agreement.signed_by_unicef_date)
        self.assertEqual(agreement.year, agreement.created.year)

    def test_year_not_saved(self):
        partner = models.PartnerOrganization(name="Partner")
        agreement = models.Agreement(partner=partner)
        self.assertEqual(agreement.year, datetime.date.today().year)

    def test_update_related_interventions(self):
        agreement = AgreementFactory(
            status=models.Agreement.DRAFT,
        )
        intervention = InterventionFactory(
            agreement=agreement,
            document_type=models.Intervention.PD,
            status=models.Intervention.SIGNED,
        )
        agreement_old = copy.deepcopy(agreement)
        agreement.status = models.Agreement.TERMINATED
        agreement.update_related_interventions(agreement_old)
        self.assertNotEqual(intervention.status, agreement.status)
        intervention_updated = models.Intervention.objects.get(
            pk=intervention.pk
        )
        self.assertEqual(intervention_updated.status, agreement.status)


class TestAgreementAmendment(TenantTestCase):
    def test_unicode(self):
        agreement = AgreementFactory()
        amendment = AgreementAmendmentFactory(
            agreement=agreement
        )
        self.assertEqual(
            unicode(amendment),
            "{} {}".format(agreement.reference_number, amendment.number)
        )


class TestInterventionAmendment(TenantTestCase):
    def test_unicode(self):
        ia = models.InterventionAmendment(
            amendment_number="123",
            signed_date=None
        )
        self.assertEqual(unicode(ia), "123:- None")
        ia.signed_date = datetime.date(2001, 1, 1)
        self.assertEqual(unicode(ia), "123:- 2001-01-01")

    def test_compute_reference_number_no_amendments(self):
        intervention = InterventionFactory()
        ia = models.InterventionAmendment(intervention=intervention)
        self.assertEqual(ia.compute_reference_number(), 1)

    def test_compute_reference_number(self):
        intervention = InterventionFactory()
        InterventionAmendmentFactory(
            intervention=intervention,
            signed_date=datetime.date.today()
        )
        ia = models.InterventionAmendment(intervention=intervention)
        self.assertEqual(ia.compute_reference_number(), 2)


class TestInterventionResultLink(TenantTestCase):
    def test_unicode(self):
        intervention = InterventionFactory()
        result = ResultFactory(
            name="Name",
            code="Code"
        )
        link = InterventionResultLinkFactory(
            intervention=intervention,
            cp_output=result,
        )
        intervention_str = str(intervention)
        result_str = str(result)
        self.assertEqual(
            unicode(link),
            "{} {}".format(intervention_str, result_str)
        )


class TestInterventionBudget(TenantTestCase):
    def test_str(self):
        intervention = InterventionFactory()
        intervention_str = str(intervention)
        budget = InterventionBudgetFactory(
            intervention=intervention,
            unicef_cash=10.00,
            in_kind_amount=5.00,
            partner_contribution=20.00,
        )
        self.assertEqual(str(budget), "{}: 35.00".format(intervention_str))


class TestFileType(TenantTestCase):
    def test_unicode(self):
        f = models.FileType(name="FileType")
        self.assertEqual(unicode(f), "FileType")


class TestInterventionAttachment(TenantTestCase):
    def test_unicode(self):
        a = models.InterventionAttachment(attachment="test.pdf")
        self.assertEqual(unicode(a), "test.pdf")


class TestInterventionReportingPeriod(TenantTestCase):
    def test_str(self):
        intervention = InterventionFactory()
        intervention_str = str(intervention)
        period = InterventionReportingPeriodFactory(
            intervention=intervention,
            start_date=datetime.date(2001, 1, 1),
            end_date=datetime.date(2002, 2, 2),
            due_date=datetime.date(2003, 3, 3),
        )
        self.assertEqual(
            str(period),
            "{} (2001-01-01 - 2002-02-02) due on 2003-03-03".format(
                intervention_str
            )
        )
