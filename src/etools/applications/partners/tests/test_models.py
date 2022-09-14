import copy
import datetime
from decimal import Decimal
from unittest import skip
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import connection
from django.test import SimpleTestCase
from django.urls import reverse
from django.utils import timezone

from freezegun import freeze_time

from etools.applications.audit.models import Engagement
from etools.applications.audit.tests.factories import AuditFactory, SpecialAuditFactory, SpotCheckFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.funds.tests.factories import FundsReservationHeaderFactory
from etools.applications.partners import models
from etools.applications.partners.models import InterventionSupplyItem
from etools.applications.partners.tests.factories import (
    AgreementAmendmentFactory,
    AgreementFactory,
    AssessmentFactory,
    FileTypeFactory,
    InterventionAmendmentFactory,
    InterventionAttachmentFactory,
    InterventionBudgetFactory,
    InterventionFactory,
    InterventionPlannedVisitsFactory,
    InterventionReportingPeriodFactory,
    InterventionResultLinkFactory,
    InterventionSupplyItemFactory,
    PartnerFactory,
    PartnerPlannedVisitsFactory,
    PartnerStaffFactory,
    PlannedEngagementFactory,
    WorkspaceFileTypeFactory,
)
from etools.applications.publics.tests.factories import PublicsCurrencyFactory
from etools.applications.reports.tests.factories import (
    AppliedIndicatorFactory,
    CountryProgrammeFactory,
    InterventionActivityFactory,
    LowerResultFactory,
    ResultFactory,
)
from etools.applications.t2f.models import Travel, TravelType
from etools.applications.t2f.tests.factories import TravelActivityFactory, TravelFactory
from etools.applications.tpm.models import TPMVisit
from etools.applications.tpm.tests.factories import TPMActivityFactory, TPMVisitFactory
from etools.applications.users.tests.factories import UserFactory


def get_date_from_prior_year():
    """Return a date for which year < the current year"""
    return datetime.date.today() - datetime.timedelta(days=700)


class TestAgreementNumberGeneration(BaseTenantTestCase):
    """Test that agreements have the expected base and reference numbers for all types of agreements"""
    @classmethod
    def setUpTestData(cls):
        cls.date = datetime.date.today()
        cls.tenant.country_short_code = 'LEBA'
        cls.tenant.save()

    def test_reference_number_pca(self):
        """Thoroughly exercise agreement reference numbers for PCA"""
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
        """Verify simple agreement reference # generation for all agreement types"""
        reference_number_template = 'LEBA/{agreement_type}' + str(self.date.year) + '{id}'
        agreement_types = [agreement_type[0] for agreement_type in models.Agreement.AGREEMENT_TYPES]
        for agreement_type in agreement_types:
            agreement = AgreementFactory(agreement_type=agreement_type)
            expected_reference_number = reference_number_template.format(
                agreement_type=agreement_type, id=agreement.id)
            self.assertEqual(agreement.reference_number, expected_reference_number)

    def test_base_number_generation(self):
        """Verify correct values in the .base_number attribute"""
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
        """Exercise Agreement.update_reference_number()"""
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


class TestHACTCalculations(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        year = datetime.date.today().year
        cls.intervention = InterventionFactory(
            status='active'
        )
        CountryProgrammeFactory(
            name='Current Country Programme',
            from_date=datetime.date(year, 1, 1),
            to_date=datetime.date(year + 1, 12, 31)
        )
        cls.intervention.planned_budget.partner_contribution = 10000
        cls.intervention.planned_budget.unicef_cash = 60000
        cls.intervention.planned_budget.in_kind_amount = 5000
        cls.intervention.planned_budget.save()


class TestPartnerOrganizationModel(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        self.partner_organization = PartnerFactory(
            name="Partner Org 1",
            total_ct_ytd=models.PartnerOrganization.CT_CP_AUDIT_TRIGGER_LEVEL + 1,
            reported_cy=models.PartnerOrganization.CT_CP_AUDIT_TRIGGER_LEVEL + 1,
            last_assessment_date=datetime.date(2000, 5, 14),
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

    def assert_min_requirements(self, programmatic_visit, spot_check):
        """common assert for minimum requirement calculation"""
        hact_min_req = self.partner_organization.hact_min_requirements
        data = {
            "audits": 0,
            "programmatic_visits": programmatic_visit,
            "spot_checks": spot_check,
        }
        self.assertEqual(hact_min_req, data)

    def test_get_last_pca(self):
        pca = self.partner_organization.get_last_pca
        self.assertEqual(pca, self.pca_signed1)

    @freeze_time('2013-08-13')
    def test_expiring_assessment_flag_true(self):
        self.assertTrue(self.partner_organization.expiring_assessment_flag)

    @freeze_time('2000-05-14')
    def test_expiring_assessment_flag_false(self):
        self.assertFalse(self.partner_organization.expiring_assessment_flag)

    def test_approaching_threshold_flag_true(self):
        self.partner_organization.highest_risk_rating_name = models.PartnerOrganization.RATING_NOT_REQUIRED
        self.partner_organization.rating = models.PartnerOrganization.RATING_LOW_RISK_ASSUMED
        self.assertTrue(self.partner_organization.approaching_threshold_flag)

    def test_approaching_threshold_flag_false(self):
        self.partner_organization.highest_risk_rating_name = models.PartnerOrganization.RATING_NOT_REQUIRED
        self.partner_organization.rating = models.PartnerOrganization.RATING_LOW
        self.partner_organization.total_ct_ytd = models.PartnerOrganization.CT_CP_AUDIT_TRIGGER_LEVEL - 1
        self.assertFalse(self.partner_organization.approaching_threshold_flag)

    def test_approaching_threshold_flag_false_moderate(self):
        self.partner_organization.highest_risk_rating_name = models.PartnerOrganization.RATING_MEDIUM
        self.partner_organization.rating = models.PartnerOrganization.RATING_HIGH
        self.assertFalse(self.partner_organization.approaching_threshold_flag)

    def test_hact_min_requirements_ct_under_25k(self):
        self.partner_organization.net_ct_cy = 0
        self.partner_organization.reported_cy = 0
        hact_min_req = self.partner_organization.hact_min_requirements
        data = {
            "audits": 0,
            "programmatic_visits": 0,
            "spot_checks": 0,
        }
        self.assertEqual(hact_min_req, data)

    def test_hact_min_requirements_ct_between_25k_and_50k(self):
        self.partner_organization.net_ct_cy = 44000.00
        self.partner_organization.reported_cy = 44000.00
        self.assert_min_requirements(1, 0)

    def test_hact_min_requirements_ct_between_25k_and_100k(self):
        self.partner_organization.net_ct_cy = 99000.00
        self.partner_organization.reported_cy = 99000.00
        self.assert_min_requirements(1, 1)

    def test_hact_min_requirements_ct_between_25k_and_100k_low_risk(self):
        self.partner_organization.net_ct_cy = 99000.00
        self.partner_organization.reported_cy = 99000.00
        self.partner_organization.type_of_assessment = 'Low Risk Assumed'
        self.assert_min_requirements(1, 0)

    def test_hact_min_requirements_ct_between_100k_and_500k_high(self):
        self.partner_organization.net_ct_cy = 490000.00
        self.partner_organization.reported_cy = 490000.00
        self.partner_organization.highest_risk_rating_name = models.PartnerOrganization.RATING_HIGH_RISK_ASSUMED
        self.partner_organization.rating = models.PartnerOrganization.RATING_MEDIUM
        self.assert_min_requirements(3, 1)

    def test_hact_min_requirements_ct_between_100k_and_500k_significant(self):
        self.partner_organization.net_ct_cy = 490000.00
        self.partner_organization.reported_cy = 490000.00
        self.partner_organization.highest_risk_rating_name = models.PartnerOrganization.RATING_SIGNIFICANT
        self.partner_organization.rating = models.PartnerOrganization.RATING_MEDIUM
        self.assert_min_requirements(3, 1)

    def test_hact_min_requirements_ct_between_100k_and_500k_moderate(self):
        self.partner_organization.net_ct_cy = 490000.00
        self.partner_organization.reported_cy = 490000.00
        self.partner_organization.highest_risk_rating_name = models.PartnerOrganization.RATING_MEDIUM
        self.partner_organization.rating = models.PartnerOrganization.RATING_LOW
        self.assert_min_requirements(2, 1)

    def test_hact_min_requirements_ct_between_100k_and_500k_low(self):
        self.partner_organization.net_ct_cy = 490000.00
        self.partner_organization.reported_cy = 490000.00
        self.partner_organization.highest_risk_rating_name = models.PartnerOrganization.RATING_LOW
        self.partner_organization.rating = models.PartnerOrganization.RATING_HIGH
        self.assert_min_requirements(1, 1)

    def test_hact_min_requirements_ct_over_500k_high(self):
        self.partner_organization.net_ct_cy = 510000.00
        self.partner_organization.reported_cy = 510000.00
        self.partner_organization.highest_risk_rating_name = models.PartnerOrganization.RATING_HIGH
        self.partner_organization.rating = models.PartnerOrganization.RATING_MEDIUM
        self.assert_min_requirements(4, 1)

    def test_hact_min_requirements_ct_over_500k_significant(self):
        self.partner_organization.net_ct_cy = 510000.00
        self.partner_organization.reported_cy = 510000.00
        self.partner_organization.highest_risk_rating_name = models.PartnerOrganization.RATING_SIGNIFICANT
        self.partner_organization.rating = models.PartnerOrganization.RATING_LOW
        self.assert_min_requirements(4, 1)

    def test_hact_min_requirements_ct_over_500k_moderate(self):
        self.partner_organization.net_ct_cy = 510000.00
        self.partner_organization.reported_cy = 510000.00
        self.partner_organization.highest_risk_rating_name = models.PartnerOrganization.RATING_MEDIUM
        self.partner_organization.rating = models.PartnerOrganization.RATING_LOW
        self.assert_min_requirements(3, 1)

    def test_hact_min_requirements_ct_over_500k_low(self):
        self.partner_organization.net_ct_cy = 510000.00
        self.partner_organization.reported_cy = 510000.00
        self.partner_organization.highest_risk_rating_name = models.PartnerOrganization.RATING_LOW_RISK_ASSUMED
        self.partner_organization.rating = models.PartnerOrganization.RATING_MEDIUM
        self.assert_min_requirements(2, 1)

    def test_planned_visits_gov(self):
        self.partner_organization.partner_type = models.PartnerType.GOVERNMENT
        self.partner_organization.save()
        year = datetime.date.today().year
        PartnerPlannedVisitsFactory(
            partner=self.partner_organization,
            year=year,
            programmatic_q1=3
        )
        PartnerPlannedVisitsFactory(
            partner=self.partner_organization,
            year=year - 1,
            programmatic_q3=2
        )
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['planned']['total'], 3)

    def test_planned_visits_non_gov(self):
        self.partner_organization.partner_type = models.PartnerType.UN_AGENCY
        self.partner_organization.save()
        year = datetime.date.today().year
        PartnerPlannedVisitsFactory(
            partner=self.partner_organization,
            year=year,
            programmatic_q1=3,
            programmatic_q4=4,
        )
        intervention = InterventionFactory(
            agreement=self.pca_signed1,
            status=models.Intervention.ACTIVE
        )
        InterventionPlannedVisitsFactory(
            intervention=intervention,
            year=year - 1,
            programmatic_q2=2
        )
        InterventionPlannedVisitsFactory(
            intervention=intervention,
            year=year,
            programmatic_q1=1,
            programmatic_q3=3,
        )
        self.partner_organization.update_planned_visits_to_hact()
        self.assertEqual(
            self.partner_organization.hact_values['programmatic_visits']['planned']['total'],
            4
        )

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
            programmatic_q1=1,
            programmatic_q3=3,
        )
        InterventionPlannedVisitsFactory(
            intervention=intervention2,
            year=year - 1,
            programmatic_q4=2
        )
        self.partner_organization.update_planned_visits_to_hact()
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['planned']['total'], 4)
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['planned']['q3'], 3)

    def test_programmatic_visits_update_one(self):
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['total'], 0)
        self.partner_organization.update_programmatic_visits(
            event_date=datetime.datetime(2013, 5, 26),
            update_one=True
        )
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['total'], 1)
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['q1'], 0)
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['q2'], 1)
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['q3'], 0)
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['q4'], 0)

    def test_programmatic_visits_update_travel_activity(self):
        tz = timezone.get_default_timezone()
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['total'], 0)
        traveller = UserFactory()
        travel = TravelFactory(
            traveler=traveller,
            status=Travel.COMPLETED,
            end_date=datetime.datetime(datetime.datetime.today().year, 9, 1, tzinfo=tz)
        )
        TravelActivityFactory(
            travels=[travel],
            primary_traveler=traveller,
            travel_type=TravelType.PROGRAMME_MONITORING,
            partner=self.partner_organization,
        )
        self.partner_organization.update_programmatic_visits()
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['total'], 1)
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['q1'], 0)
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['q2'], 0)
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['q3'], 1)
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['q4'], 0)

    def test_programmatic_visits_update_tpm_visit(self):
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['total'], 0)
        visit = TPMVisitFactory(
            status=TPMVisit.UNICEF_APPROVED,
        )
        visit2 = TPMVisitFactory(
            status=TPMVisit.UNICEF_APPROVED,
            date_of_unicef_approved=datetime.datetime(datetime.datetime.today().year, 5, 20)
        )
        TPMActivityFactory(
            tpm_visit=visit,
            partner=self.partner_organization,
            is_pv=True,
            date=datetime.datetime(datetime.datetime.today().year, 5, 1)
        )
        TPMActivityFactory(
            tpm_visit=visit,
            partner=self.partner_organization,
            is_pv=True,
            date=datetime.datetime(datetime.datetime.today().year, 9, 1)
        )
        TPMActivityFactory(
            tpm_visit=visit,
            partner=self.partner_organization,
            date=datetime.datetime(datetime.datetime.today().year, 5, 1)
        )
        TPMActivityFactory(
            tpm_visit=visit2,
            partner=self.partner_organization,
            date=datetime.datetime(datetime.datetime.today().year, 5, 1)
        )

        self.partner_organization.update_programmatic_visits()
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['total'], 2)
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['q1'], 0)
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['q2'], 1)
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['q3'], 1)
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['q4'], 0)

    @freeze_time("2013-12-26")
    def test_spot_checks_update_one(self):
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['total'], 0)
        self.partner_organization.update_spot_checks(update_one=True)
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['total'], 1)
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['q1'], 0)
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['q2'], 0)
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['q3'], 0)
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['q4'], 1)

    @freeze_time("2013-12-26")
    def test_spot_checks_update_one_with_date(self):
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['total'], 0)
        self.partner_organization.update_spot_checks(
            update_one=True,
            event_date=datetime.datetime(2013, 5, 12)
        )
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['total'], 1)
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['q1'], 0)
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['q2'], 1)
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['q3'], 0)
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['q4'], 0)

    def test_spot_checks_update_travel_activity(self):
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['total'], 0)
        SpotCheckFactory(
            partner=self.partner_organization,
            status=Engagement.FINAL,
            date_of_draft_report_to_ip=datetime.datetime(datetime.datetime.today().year, 4, 1)
        )
        SpotCheckFactory(
            partner=self.partner_organization,
            status=Engagement.CANCELLED,
            date_of_draft_report_to_ip=datetime.datetime(datetime.datetime.today().year, 4, 10)
        )
        SpotCheckFactory(
            partner=self.partner_organization,
            status=Engagement.REPORT_SUBMITTED,
            date_of_draft_report_to_ip=None
        )
        self.partner_organization.update_spot_checks()
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['total'], 1)
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['q1'], 0)
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['q2'], 1)
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['q3'], 0)
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['q4'], 0)

    @freeze_time("2013-12-26")
    def test_audits_completed_update_one(self):
        self.assertEqual(self.partner_organization.hact_values['audits']['completed'], 0)
        self.partner_organization.update_audits_completed(
            update_one=True,
        )
        self.assertEqual(self.partner_organization.hact_values['audits']['completed'], 1)

    def test_audits_completed_update_travel_activity(self):
        self.assertEqual(self.partner_organization.hact_values['audits']['completed'], 0)
        AuditFactory(
            partner=self.partner_organization,
            status=Engagement.FINAL,
            date_of_draft_report_to_ip=datetime.datetime(datetime.datetime.today().year, 4, 1)
        )
        SpecialAuditFactory(
            partner=self.partner_organization,
            status=Engagement.REPORT_SUBMITTED,
            date_of_draft_report_to_ip=datetime.datetime(datetime.datetime.today().year, 8, 1)
        )
        AuditFactory(
            partner=self.partner_organization,
            status=Engagement.FINAL,
            date_of_draft_report_to_ip=None
        )
        SpecialAuditFactory(
            partner=self.partner_organization,
            status=Engagement.CANCELLED,
            date_of_draft_report_to_ip=datetime.datetime(datetime.datetime.today().year, 8, 1)
        )
        self.partner_organization.update_audits_completed()
        self.assertEqual(self.partner_organization.hact_values['audits']['completed'], 2)

    def test_partner_organization_get_admin_url(self):
        "Test that get_admin_url produces the URL we expect."
        admin_url = self.partner_organization.get_admin_url()
        expected = reverse('admin:partners_partnerorganization_change', args=[self.partner_organization.id])
        self.assertEqual(admin_url, expected)


class TestAgreementModel(BaseTenantTestCase):
    def setUp(self):
        super().setUp()

        self.partner_organization = PartnerFactory(
            name="Partner Org 1",
        )
        self.cp = CountryProgrammeFactory(
            name="CP 1",
            wbs="0001/A0/01",
            from_date=datetime.date(datetime.date.today().year - 1, 1, 1),
            to_date=datetime.date(datetime.date.today().year + 1, 1, 1),
        )
        self.agreement = AgreementFactory(
            agreement_type=models.Agreement.PCA,
            partner=self.partner_organization,
            country_programme=self.cp,
            signed_by_unicef_date=datetime.date(datetime.date.today().year - 1, 5, 1),
            signed_by_partner_date=datetime.date(datetime.date.today().year - 1, 4, 1),
        )

    def test_reference_number(self):
        self.assertIn("PCA", self.agreement.reference_number)

    def test_start_date_unicef_date(self):
        self.assertEqual(self.agreement.start, self.agreement.signed_by_unicef_date)

    def test_start_date_partner_date(self):
        self.agreement.signed_by_partner_date = datetime.date(datetime.date.today().year - 1, 7, 1)
        self.agreement.save()
        self.assertEqual(self.agreement.start, self.agreement.signed_by_partner_date)

    def test_start_date_programme_date(self):
        self.agreement.signed_by_unicef_date = datetime.date(datetime.date.today().year - 2, 1, 1)
        self.agreement.signed_by_partner_date = datetime.date(datetime.date.today().year - 2, 1, 1)
        self.agreement.save()
        self.assertEqual(self.agreement.start, self.cp.from_date)


class TestInterventionModel(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        call_command('update_notifications')
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

    def test_str(self):
        number = self.intervention.number
        self.assertEqual(str(self.intervention), number)

    def test_permission_structure(self):
        permissions = models.Intervention.permission_structure()
        self.assertTrue(isinstance(permissions, dict))
        self.assertEqual(permissions["amendments"], {
            'view': {'false': [
                {'group': 'Partner User', 'condition': '', 'status': '*'},
                {'group': '*', 'condition': 'user_adds_amendment', 'status': '*'},
                {'group': '*', 'condition': '', 'status': 'draft'}
            ]},
            'edit': {
                'true': [
                    {'status': 'signed', 'group': 'Unicef Focal Point', 'condition': 'not_in_amendment_mode'},
                    {'status': 'active', 'group': 'Unicef Focal Point', 'condition': 'not_in_amendment_mode'},
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

    @skip("fr_currency property on intervention is being deprecated")
    def test_default_budget_currency(self):
        intervention = InterventionFactory()
        intervention.planned_budget.currency = "USD"
        intervention.planned_budget.save()
        self.assertEqual(intervention.default_budget_currency, "USD")

    @skip("fr_currency property on intervention is being deprecated")
    def test_fr_currency_empty(self):
        self.assertIsNone(self.intervention.fr_currency)

    @skip("fr_currency property on intervention is being deprecated")
    def test_fr_currency(self):
        intervention = InterventionFactory()
        FundsReservationHeaderFactory(
            currency="USD",
            intervention=intervention,
        )
        self.assertEqual(intervention.fr_currency, "USD")

    def test_total_no_intervention(self):
        self.assertEqual(int(self.intervention.total_unicef_cash), 0)
        self.assertEqual(int(self.intervention.total_partner_contribution), 0)
        self.assertEqual(int(self.intervention.total_budget), 0)
        self.assertEqual(int(self.intervention.total_unicef_budget), 0)

    def _prepare_budgets(self):
        self.intervention.management_budgets.act1_unicef = 5
        self.intervention.management_budgets.act2_unicef = 5
        self.intervention.management_budgets.act1_partner = 5
        self.intervention.management_budgets.act3_partner = 15
        self.intervention.management_budgets.save()
        InterventionActivityFactory(
            unicef_cash=2, cso_cash=3, result__result_link=InterventionResultLinkFactory(intervention=self.intervention)
        )
        InterventionSupplyItemFactory(intervention=self.intervention, unit_number=5, unit_price=2)
        InterventionSupplyItemFactory(intervention=self.intervention, unit_number=1, unit_price=4)

    def test_total_unicef_cash(self):
        self._prepare_budgets()
        # 2 (activity.unicef_cash) + sum of unicef act from management budgets (5 + 5)
        self.assertEqual(int(self.intervention.total_unicef_cash), 12)

    def test_total_partner_contribution(self):
        self._prepare_budgets()
        # 3 (activity.cso_cash) + sum of partner act from management budgets (5 + 15)
        self.assertEqual(int(self.intervention.total_partner_contribution), 23)

    def test_total_in_kind_amount(self):
        self._prepare_budgets()
        # 5*2 + 1*4 (sum of items total price)
        self.assertEqual(int(self.intervention.total_in_kind_amount), 14)

    def test_total_budget(self):
        self._prepare_budgets()
        # 12 (total_unicef_cash) + 23 (total_partner_contribution) + 14 (total_in_kind_amount)
        self.assertEqual(int(self.intervention.total_budget), 49)

    def test_total_unicef_budget(self):
        self._prepare_budgets()
        # 12 (total_unicef_cash) + 14 (total_in_kind_amount)
        self.assertEqual(int(self.intervention.total_unicef_budget), 26)

    def test_year(self):
        """Exercise the year property"""
        self.assertIsNone(self.intervention.signed_by_unicef_date)
        self.assertEqual(self.intervention.year, self.intervention.created.year)
        self.intervention.signed_by_unicef_date = get_date_from_prior_year()
        self.assertEqual(self.intervention.year, self.intervention.signed_by_unicef_date.year)

    def test_year_no_pk(self):
        i = models.Intervention()
        self.assertEqual(i.year, datetime.date.today().year)

    def test_reference_number(self):
        """Exercise the reference number property"""
        expected_reference_number = self.intervention.agreement.base_number + '/' + self.intervention.document_type
        expected_reference_number += str(self.intervention.created.year) + \
            str(self.intervention.id)
        self.assertEqual(self.intervention.reference_number, expected_reference_number)

        self.intervention.signed_by_unicef_date = get_date_from_prior_year()

        expected_reference_number = self.intervention.agreement.base_number + '/' + self.intervention.document_type
        expected_reference_number += \
            str(self.intervention.reference_number_year) + str(self.intervention.id)
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
        self.assertCountEqual(intervention.all_lower_results, [
            lower_result_1,
            lower_result_2,
        ])

    def test_intervention_clusters_empty(self):
        self.assertFalse(self.intervention.intervention_clusters())

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
            cluster_name='',
        )
        AppliedIndicatorFactory(lower_result=lower_result_2)
        self.assertCountEqual(intervention.intervention_clusters(), [
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
            total_amt=0.00,
            total_amt_local=10.00,
            outstanding_amt=0.00,
            outstanding_amt_local=20.00,
            intervention_amt=30.00,
            actual_amt=0.00,
            actual_amt_local=40.00,
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
            total_amt=0.00,
            total_amt_local=10.00,
            outstanding_amt=0.00,
            outstanding_amt_local=20.00,
            intervention_amt=30.00,
            actual_amt=0.00,
            actual_amt_local=40.00,
            start_date=datetime.date(2010, 1, 1),
            end_date=datetime.date(2002, 1, 1),
        )
        FundsReservationHeaderFactory(
            intervention=intervention,
            total_amt=0.00,
            total_amt_local=10.00,
            outstanding_amt=0.00,
            outstanding_amt_local=20.00,
            intervention_amt=30.00,
            actual_amt=0.00,
            actual_amt_local=40.00,
            start_date=datetime.date(2001, 1, 1),
            end_date=datetime.date(2020, 1, 1),
        )
        FundsReservationHeaderFactory(
            intervention=intervention,
            total_amt=0.00,
            total_amt_local=10.00,
            outstanding_amt=0.00,
            outstanding_amt_local=20.00,
            intervention_amt=30.00,
            actual_amt=0.00,
            actual_amt_local=40.00,
            start_date=datetime.date(2005, 1, 1),
            end_date=datetime.date(2010, 1, 1),
        )
        self.validate_total_frs(
            intervention.total_frs,
            10.00 * 3,
            20.00 * 3,
            30.00 * 3,
            40.00 * 3,
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

    def test_planned_budget(self):
        currency = "PEN"
        budget_qs = models.InterventionBudget.objects.filter(
            currency=currency,
        )
        self.assertFalse(budget_qs.exists())
        country = connection.tenant
        country.local_currency = PublicsCurrencyFactory(code=currency)
        country.local_currency.save()
        mock_tenant = Mock(tenant=country)
        with patch("etools.applications.partners.models.connection", mock_tenant):
            InterventionFactory()
        self.assertTrue(budget_qs.exists())

    def test_hq_support_cost(self):
        partner = PartnerFactory(
            cso_type=models.PartnerOrganization.CSO_TYPE_COMMUNITY,
        )
        intervention = InterventionFactory(agreement__partner=partner)
        self.assertEqual(intervention.hq_support_cost, 0.0)

        # INGO type
        partner = PartnerFactory(
            cso_type=models.PartnerOrganization.CSO_TYPE_INTERNATIONAL,
        )
        intervention = InterventionFactory(agreement__partner=partner)
        self.assertEqual(intervention.hq_support_cost, 7.0)

        # INGO set value
        intervention = InterventionFactory(
            agreement__partner=partner,
            hq_support_cost=5.0,
        )
        self.assertEqual(intervention.hq_support_cost, 5.0)

        # update value
        intervention.hq_support_cost = 2.0
        intervention.save()
        intervention.refresh_from_db()
        self.assertEqual(intervention.hq_support_cost, 2.0)


class TestGetFilePaths(BaseTenantTestCase):
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
        p = models.get_assessment_path(assessment, "test.pdf")
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


class TestWorkspaceFileType(BaseTenantTestCase):
    def test_str(self):
        w = models.WorkspaceFileType(name="Test")
        self.assertEqual(str(w), "Test")


class TestPartnerOrganization(BaseTenantTestCase):
    def test_str(self):
        p = models.PartnerOrganization(name="Test Partner Org")
        self.assertEqual(str(p), "Test Partner Org")

    def test_save(self):
        p = models.PartnerOrganization(
            name="Test",
            hact_values={'all': 'good'}
        )
        p.save()
        self.assertIsNotNone(p.pk)


class TestPartnerStaffMember(BaseTenantTestCase):
    def test_str(self):
        partner = models.PartnerOrganization(name="Partner")
        staff = models.PartnerStaffMember(
            first_name="First",
            last_name="Last",
            partner=partner
        )
        self.assertEqual(str(staff), "First Last (Partner)")

    def test_save_update_deactivate(self):
        partner = PartnerFactory()
        staff = PartnerStaffFactory(
            partner=partner,
        )
        staff.user.profile.countries_available.add(connection.tenant)
        self.assertTrue(staff.active)

        staff.active = False
        staff.save()

        self.assertEqual(staff.user.is_active, False)
        self.assertEqual(staff.user.profile.country, None)
        self.assertEqual(staff.user.profile.countries_available.filter(id=connection.tenant.id).exists(), False)

    def test_save_update_reactivate(self):
        partner = PartnerFactory()
        staff = PartnerStaffFactory(
            partner=partner,
            active=False,
        )
        staff.user.profile.countries_available.remove(connection.tenant)
        self.assertFalse(staff.active)

        staff.active = True
        staff.save()

        self.assertEqual(staff.user.is_active, True)
        self.assertEqual(staff.user.profile.country, connection.tenant)
        self.assertEqual(staff.user.profile.countries_available.filter(id=connection.tenant.id).exists(), True)


class TestAssessment(BaseTenantTestCase):
    def test_str_not_completed(self):
        partner = models.PartnerOrganization(name="Partner")
        a = models.Assessment(
            partner=partner,
            type="Type",
            rating="Rating",
        )
        self.assertEqual(str(a), "Type: Partner Rating NOT COMPLETED")

    def test_str_completed(self):
        partner = models.PartnerOrganization(name="Partner")
        a = models.Assessment(
            partner=partner,
            type="Type",
            rating="Rating",
            completed_date=datetime.date(2001, 1, 1)
        )
        self.assertEqual(str(a), "Type: Partner Rating 01-01-2001")


class TestAgreement(BaseTenantTestCase):
    def test_str(self):
        partner = models.PartnerOrganization(name="Partner")
        agreement = models.Agreement(
            partner=partner,
            agreement_type=models.Agreement.DRAFT,
        )
        self.assertEqual(str(agreement), "draft for Partner ( - )")

    def test_str_dates(self):
        partner = models.PartnerOrganization(name="Partner")
        agreement = models.Agreement(
            partner=partner,
            agreement_type=models.Agreement.DRAFT,
            start=datetime.date(2001, 1, 1),
            end=datetime.date(2002, 1, 1),
        )
        self.assertEqual(
            str(agreement),
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


class TestAgreementAmendment(BaseTenantTestCase):
    def test_str(self):
        agreement = AgreementFactory()
        amendment = AgreementAmendmentFactory(
            agreement=agreement
        )
        self.assertEqual(
            str(amendment),
            "{} {}".format(agreement.reference_number, amendment.number)
        )


class TestInterventionAmendment(BaseTenantTestCase):
    def test_str(self):
        ia = models.InterventionAmendment(
            amendment_number="123",
            signed_date=None
        )
        self.assertEqual(str(ia), "123:- None")
        ia.signed_date = datetime.date(2001, 1, 1)
        self.assertEqual(str(ia), "123:- 2001-01-01")

    def test_compute_reference_number_no_amendments(self):
        intervention = InterventionFactory()
        ia = models.InterventionAmendment(intervention=intervention)
        self.assertEqual(ia.compute_reference_number(), 'amd/1')

    def test_compute_reference_number(self):
        intervention = InterventionFactory()
        InterventionAmendmentFactory(
            intervention=intervention,
            signed_date=datetime.date.today()
        )
        ia = models.InterventionAmendment(intervention=intervention)
        self.assertEqual(ia.compute_reference_number(), 'amd/2')


class TestInterventionResultLink(BaseTenantTestCase):
    def test_str(self):
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
            str(link),
            "{} {}".format(intervention_str, result_str)
        )

    def test_total(self):
        intervention = InterventionFactory()
        result = ResultFactory(
            name="Name",
            code="Code"
        )
        link = InterventionResultLinkFactory(
            intervention=intervention,
            cp_output=result,
        )

        # empty
        self.assertEqual(link.total(), 0)

        # lower results
        ll = LowerResultFactory(result_link=link)
        InterventionActivityFactory(result=ll, unicef_cash=10, cso_cash=20)
        self.assertEqual(link.total(), 30)

    def test_auto_code(self):
        link1 = InterventionResultLinkFactory()
        link2 = InterventionResultLinkFactory(intervention=link1.intervention)
        link0 = InterventionResultLinkFactory(intervention=link1.intervention, cp_output=None)
        InterventionResultLinkFactory()
        link3 = InterventionResultLinkFactory(intervention=link1.intervention)
        self.assertEqual(link1.code, '1')
        self.assertEqual(link2.code, '2')
        self.assertEqual(link0.code, '0')
        self.assertEqual(link3.code, '3')

    def test_code_renumber_on_result_link_delete(self):
        intervention = InterventionFactory()
        result_link_1 = InterventionResultLinkFactory(intervention=intervention, code=None)
        result_link_2 = InterventionResultLinkFactory(intervention=intervention, code=None)
        result_link_3 = InterventionResultLinkFactory(intervention=intervention, code=None)

        self.assertEqual(result_link_1.code, '1')
        self.assertEqual(result_link_2.code, '2')
        self.assertEqual(result_link_3.code, '3')

        result_link_2.delete()

        result_link_1.refresh_from_db()
        result_link_3.refresh_from_db()
        self.assertEqual(result_link_1.code, '1')
        self.assertEqual(result_link_3.code, '2')


class TestInterventionBudget(BaseTenantTestCase):
    def test_str(self):
        intervention = InterventionFactory()
        intervention_str = str(intervention)

        mgmt_budget = intervention.management_budgets
        mgmt_budget.act1_unicef = 10
        mgmt_budget.act1_partner = 5
        mgmt_budget.act2_partner = 15
        mgmt_budget.save()

        InterventionSupplyItemFactory(intervention=intervention, unit_number=1, unit_price=5)

        self.assertEqual(intervention.planned_budget.unicef_cash_local, 10)
        self.assertEqual(intervention.planned_budget.in_kind_amount_local, 5)
        self.assertEqual(intervention.planned_budget.partner_contribution_local, 20)
        self.assertEqual(str(intervention.planned_budget), "{}: 35.00".format(intervention_str))
        self.assertEqual(
            intervention.planned_budget.total_cash_local(),
            20 + 10,
        )

    def test_default_currency(self):
        # no default currency
        intervention_1 = InterventionFactory()
        self.assertEqual(intervention_1.planned_budget.currency, "USD")

        # with default currency
        currency = "ZAR"
        country = connection.tenant
        country.local_currency = PublicsCurrencyFactory(code=currency)
        country.local_currency.save()
        mock_tenant = Mock(tenant=country)
        with patch("etools.applications.partners.models.connection", mock_tenant):
            intervention = InterventionFactory()
        self.assertEqual(intervention.planned_budget.currency, currency)

    def test_calc_totals_no_assoc(self):
        intervention = InterventionFactory()
        mgmt_budget = intervention.management_budgets
        budget = intervention.planned_budget

        mgmt_budget.act1_unicef = 20
        mgmt_budget.act1_partner = 10
        mgmt_budget.save()

        InterventionSupplyItemFactory(intervention=intervention, unit_number=6, unit_price=5)

        self.assertEqual(budget.partner_contribution_local, 10)
        self.assertEqual(budget.unicef_cash_local, 20)
        self.assertEqual(budget.in_kind_amount_local, 30)
        self.assertEqual(budget.programme_effectiveness, 50)  # = mgmt_budget.total
        self.assertEqual(
            "{:0.2f}".format(budget.partner_contribution_percent),
            "{:0.2f}".format(10 / (10 + 20 + 30) * 100),
        )
        self.assertEqual(budget.total_cash_local(), 10 + 20)

    def test_calc_totals_results(self):
        intervention = InterventionFactory()
        mgmt_budget = intervention.management_budgets
        budget = intervention.planned_budget

        mgmt_budget.act1_unicef = 20
        mgmt_budget.act1_partner = 10
        mgmt_budget.save()

        InterventionSupplyItemFactory(intervention=intervention, unit_number=6, unit_price=5)

        link = InterventionResultLinkFactory(intervention=budget.intervention)
        lower_result = LowerResultFactory(result_link=link)
        for __ in range(3):
            InterventionActivityFactory(
                result=lower_result,
                unicef_cash=101,
                cso_cash=202,
            )

        self.assertEqual(budget.partner_contribution_local, 202 * 3 + 10)  # 616
        self.assertEqual(budget.unicef_cash_local, 101 * 3 + 20)  # 323
        self.assertEqual(budget.in_kind_amount_local, 30)
        self.assertEqual(budget.programme_effectiveness, Decimal(30) / (616 + 323 + 30) * 100)
        self.assertEqual(
            "{:0.2f}".format(budget.partner_contribution_percent),
            "{:0.2f}".format((616 / (616 + 323 + 30) * 100)),
        )
        self.assertEqual(budget.total_cash_local(), 616 + 323)

    @skip("outputs deactivation disabled")
    def test_calc_totals_inactive_result(self):
        intervention = InterventionFactory()
        mgmt_budget = intervention.management_budgets
        budget = intervention.planned_budget

        mgmt_budget.act1_unicef = 20
        mgmt_budget.act1_partner = 10
        mgmt_budget.save()

        InterventionSupplyItemFactory(intervention=intervention, unit_number=6, unit_price=5)

        link = InterventionResultLinkFactory(intervention=budget.intervention)
        inactive_result = LowerResultFactory(result_link=link, is_active=False)
        InterventionActivityFactory(result=inactive_result, unicef_cash=1000, cso_cash=1000)

        self.assertEqual(budget.partner_contribution_local, 10)
        self.assertEqual(budget.unicef_cash_local, 20)
        self.assertEqual(budget.in_kind_amount_local, 30)
        self.assertEqual(budget.programme_effectiveness, Decimal(50))
        self.assertEqual(
            "{:0.2f}".format(budget.partner_contribution_percent),
            "{:0.2f}".format((10 / (10 + 20 + 30) * 100)),
        )
        self.assertEqual(budget.total_cash_local(), 10 + 20)

    def test_calc_totals_management_budget(self):
        intervention = InterventionFactory(hq_support_cost=7)
        budget = intervention.planned_budget
        mgmt_budget = intervention.management_budgets

        budget.partner_contribution_local = 10
        budget.unicef_cash_local = 20
        budget.total_hq_cash_local = 60
        budget.save()

        InterventionSupplyItemFactory(
            intervention=intervention,
            unit_number=10,
            unit_price=3,
        )
        InterventionSupplyItemFactory(
            intervention=intervention,
            unit_number=10,
            unit_price=4,
            provided_by=InterventionSupplyItem.PROVIDED_BY_PARTNER
        )

        mgmt_budget.act1_unicef = 100
        mgmt_budget.act1_partner = 200
        mgmt_budget.act2_unicef = 300
        mgmt_budget.act2_partner = 400
        mgmt_budget.act3_unicef = 500
        mgmt_budget.act3_partner = 600
        mgmt_budget.save()

        self.assertEqual(budget.partner_contribution_local, 1200)
        self.assertEqual(budget.total_unicef_cash_local_wo_hq, 900)
        self.assertEqual(budget.total_hq_cash_local, 60)
        self.assertEqual(budget.unicef_cash_local, 900 + 60)
        self.assertEqual(budget.in_kind_amount_local, 30)
        self.assertEqual(budget.partner_supply_local, 40)
        self.assertEqual(budget.total_supply, 30 + 40)
        self.assertEqual(budget.total_partner_contribution_local, 1240)
        self.assertEqual(budget.total_local, 1200 + 900 + 60 + 40 + 30)
        self.assertEqual(
            budget.programme_effectiveness,
            ((1200 + 900) / budget.total_local * 100),
        )
        self.assertEqual(
            "{:0.2f}".format(budget.partner_contribution_percent),
            "{:0.2f}".format((1200 + 40) / (1200 + 900 + 60 + 30 + 40) * 100),
        )
        self.assertEqual(budget.total_cash_local(), 1200 + 900 + 60)
        self.assertEqual(budget.total_unicef_contribution_local(), 900 + 60 + 30)

    def test_calc_totals_supply_items(self):
        intervention = InterventionFactory()
        budget = intervention.planned_budget

        for __ in range(3):
            InterventionSupplyItemFactory(
                intervention=intervention,
                unit_number=1,
                unit_price=2,
            )

        mgmt_budget = intervention.management_budgets
        mgmt_budget.act1_unicef = 10
        mgmt_budget.act1_partner = 5
        mgmt_budget.act2_unicef = 10
        mgmt_budget.act2_partner = 5
        mgmt_budget.save()

        self.assertEqual(budget.partner_contribution_local, 10)
        self.assertEqual(budget.unicef_cash_local, 20)
        self.assertEqual(budget.in_kind_amount_local, 6)
        # programme_effectiveness (mgmt_budget.total = 30) / total_local (unicef_contrib + cso_contrib = 36.00) * 100
        self.assertEqual(budget.programme_effectiveness, Decimal('83.33333333333333333333333333'))
        self.assertEqual(
            "{:0.2f}".format(budget.partner_contribution_percent),
            "{:0.2f}".format(10 / (10 + 20 + 6) * 100),
        )
        self.assertEqual(budget.total_cash_local(), 10 + 20)


class TestInterventionManagementBudget(BaseTenantTestCase):
    def test_totals(self):
        intervention = InterventionFactory()
        budget = intervention.management_budgets
        budget.act1_unicef = 100
        budget.act1_partner = 200
        budget.act2_unicef = 300
        budget.act2_partner = 400
        budget.act3_unicef = 500
        budget.act3_partner = 600
        budget.save()
        self.assertEqual(budget.partner_total, 1200)
        self.assertEqual(budget.unicef_total, 900)
        self.assertEqual(budget.total, 2100)


class TestInterventionSupplyItem(BaseTenantTestCase):
    def test_delete(self):
        intervention = InterventionFactory()
        budget = intervention.planned_budget

        for __ in range(3):
            item = InterventionSupplyItemFactory(
                intervention=intervention,
                unit_number=1,
                unit_price=2,
            )

        self.assertEqual(budget.in_kind_amount_local, 6)

        item.delete()

        budget.refresh_from_db()
        self.assertEqual(budget.in_kind_amount_local, 4)


class TestFileType(BaseTenantTestCase):
    def test_str(self):
        f = models.FileType(name="FileType")
        self.assertEqual(str(f), "FileType")


class TestInterventionAttachment(BaseTenantTestCase):
    def test_str(self):
        a = models.InterventionAttachment(attachment="test.pdf")
        self.assertEqual(str(a), "test.pdf")


class TestInterventionReportingPeriod(BaseTenantTestCase):
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


class TestStrUnicodeSlow(BaseTenantTestCase):
    """Ensure calling str() on model instances returns the right text.

    This is the same as TestStrUnicode below, except that it tests objects that need to be saved to the database
    so it's based on BaseTenantTestCase instead of TestCase.
    """

    def test_assessment(self):
        partner = PartnerFactory(name='xyz')
        instance = AssessmentFactory(partner=partner)
        self.assertIn('xyz', str(instance))

        partner = PartnerFactory(name='R\xe4dda Barnen')
        instance = AssessmentFactory(partner=partner)
        self.assertIn('R\xe4dda Barnen', str(instance))

    def test_agreement_amendment(self):
        partner = PartnerFactory(name='xyz')
        agreement = AgreementFactory(partner=partner)
        instance = AgreementAmendmentFactory(number='xyz', agreement=agreement)
        # This model's __str__() method operates on a limited range of text, so it's not possible to challenge it
        # with non-ASCII text. As long as str() succeeds, that's all the testing we can do.
        str(instance)


class TestStrUnicode(SimpleTestCase):
    """Ensure calling str() on model instances returns the right text."""

    def test_workspace_file_type(self):
        instance = WorkspaceFileTypeFactory.build(name='xyz')
        self.assertEqual(str(instance), 'xyz')

        instance = WorkspaceFileTypeFactory.build(name='R\xe4dda Barnen')
        self.assertEqual(str(instance), 'R\xe4dda Barnen')

    def test_partner_organization(self):
        instance = PartnerFactory.build(name='xyz')
        self.assertEqual(str(instance), 'xyz')

        instance = PartnerFactory.build(name='R\xe4dda Barnen')
        self.assertEqual(str(instance), 'R\xe4dda Barnen')

    def test_partner_staff_member(self):
        partner = PartnerFactory.build(name='partner')

        instance = PartnerStaffFactory.build(first_name='xyz', partner=partner)
        self.assertTrue(str(instance).startswith('xyz'))

        instance = PartnerStaffFactory.build(first_name='R\xe4dda Barnen', partner=partner)
        self.assertTrue(str(instance).startswith('R\xe4dda Barnen'))

    def test_agreement(self):
        partner = PartnerFactory.build(name='xyz')
        instance = AgreementFactory.build(partner=partner)
        self.assertIn('xyz', str(instance))

        partner = PartnerFactory.build(name='R\xe4dda Barnen')
        instance = AgreementFactory.build(partner=partner)
        self.assertIn('R\xe4dda Barnen', str(instance))

    def test_intervention(self):
        instance = InterventionFactory.build(number='two')
        self.assertEqual('two', str(instance))

        instance = InterventionFactory.build(number='tv\xe5')
        self.assertEqual('tv\xe5', str(instance))

    def test_intervention_amendment(self):
        instance = InterventionAmendmentFactory.build()
        # This model's __str__() method operates on a limited range of text, so it's not possible to challenge it
        # with non-ASCII text. As long as str() succeeds, that's all the testing we can do.
        str(instance)

    def test_intervention_result_link(self):
        intervention = InterventionFactory.build(number='two')
        instance = InterventionResultLinkFactory.build(intervention=intervention)
        self.assertTrue(str(instance).startswith('two'))

        intervention = InterventionFactory.build(number='tv\xe5')
        instance = InterventionResultLinkFactory.build(intervention=intervention)
        self.assertTrue(str(instance).startswith('tv\xe5'))

    def test_intervention_budget(self):
        intervention = InterventionFactory.build(number='two')
        instance = InterventionBudgetFactory.build(intervention=intervention)
        self.assertTrue(str(instance).startswith('two'))

        intervention = InterventionFactory.build(number='tv\xe5')
        instance = InterventionBudgetFactory.build(intervention=intervention)
        self.assertTrue(str(instance).startswith('tv\xe5'))

    def test_file_type(self):
        instance = FileTypeFactory.build()
        # This model's __str__() method returns model constants, so it's not possible to challenge it
        # with non-ASCII text. As long as str() succeeds, that's all the testing we can do.
        str(instance)

    def test_intervention_attachment(self):
        attachment = SimpleUploadedFile(name='two.txt', content='hello world!'.encode('utf-8'))
        instance = InterventionAttachmentFactory.build(attachment=attachment)
        self.assertEqual(str(instance), 'two.txt')

        attachment = SimpleUploadedFile('tv\xe5.txt', 'hello world!'.encode('utf-8'))
        instance = InterventionAttachmentFactory.build(attachment=attachment)
        self.assertEqual(str(instance), 'tv\xe5.txt')

    def test_intervention_reporting_period(self):
        intervention = InterventionFactory.build(number='two')
        str(intervention)
        instance = InterventionReportingPeriodFactory.build(intervention=intervention)
        self.assertTrue(str(instance).startswith('two'))

        intervention = InterventionFactory.build(number='tv\xe5')
        instance = InterventionReportingPeriodFactory.build(intervention=intervention)
        self.assertTrue(str(instance).startswith('tv\xe5'))


class TestPlannedEngagement(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

        cls.engagement = PlannedEngagementFactory(
            spot_check_follow_up=3,
            spot_check_planned_q1=2,
            spot_check_planned_q2=1,
            spot_check_planned_q3=0,
            spot_check_planned_q4=0,
            scheduled_audit=True,
            special_audit=False
        )

    def test_spot_check_planned(self):
        self.assertEquals(self.engagement.total_spot_check_planned, 3)

    def test_required_audit(self):
        self.assertEquals(self.engagement.required_audit, 1)

    def test_spot_check_required(self):
        self.assertEquals(self.engagement.spot_check_required, self.engagement.partner.min_req_spot_checks + 3)

    def test_spot_check_required_with_completed_audit(self):
        partner = PartnerFactory(name="Partner")
        partner.hact_values['audits']['completed'] = 1
        partner.save()

        pe = PlannedEngagementFactory(
            partner=partner,
            spot_check_follow_up=3,
            spot_check_planned_q1=2,
            spot_check_planned_q2=1,
            spot_check_planned_q3=0,
            spot_check_planned_q4=0,
            scheduled_audit=True,
            special_audit=False
        )

        self.assertEquals(pe.spot_check_required, pe.partner.min_req_spot_checks + 2)


class TestPartnerPlannedVisits(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.partner = PartnerFactory(name="Partner")
        cls.visit = PartnerPlannedVisitsFactory(
            partner=cls.partner,
            year=datetime.date.today().year,
            programmatic_q1=1,
            programmatic_q2=2,
            programmatic_q3=3,
            programmatic_q4=4,
        )

    def test_str(self):
        self.assertEqual(str(self.visit), "Partner {}".format(self.visit.year))
