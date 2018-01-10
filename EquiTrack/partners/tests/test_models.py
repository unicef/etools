import datetime
from actstream.models import model_stream

from django.utils import timezone
from freezegun import freeze_time

from EquiTrack.stream_feed.actions import create_snapshot_activity_stream
from EquiTrack.tests.mixins import FastTenantTestCase as TenantTestCase
from EquiTrack.factories import (
    AgreementFactory,
    AgreementAmendmentFactory,
    InterventionFactory,
    InterventionPlannedVisitsFactory,
    TravelFactory,
    TravelActivityFactory,
    UserFactory,
)
from audit.models import Engagement
from audit.tests.factories import SpotCheckFactory, AuditFactory, SpecialAuditFactory

from funds.models import Donor, Grant
from reports.models import (
    CountryProgramme,
)
from partners.models import (
    Agreement,
    FundingCommitment,
    PartnerOrganization,
    Intervention,
    InterventionBudget,
    PartnerType,
)
from t2f.models import Travel, TravelType


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
        agreement_types = [agreement_type[0] for agreement_type in Agreement.AGREEMENT_TYPES]
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
        current_cp = CountryProgramme.objects.create(
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
            in_kind_amount=5000
        )

        tz = timezone.get_default_timezone()

        start = datetime.datetime.combine(current_cp.from_date, datetime.time(0, 0, 1, tzinfo=tz))
        end = current_cp.from_date + datetime.timedelta(days=200)
        end = datetime.datetime.combine(end, datetime.time(23, 59, 59, tzinfo=tz))
        FundingCommitment.objects.create(
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
        FundingCommitment.objects.create(
            start=start,
            end=end,
            grant=grant,
            fr_number='0123456789',
            wbs='Test',
            fc_type='PCA',
            expenditure_amount=40000.00
        )


class TestPartnerOrganizationModel(TenantTestCase):
    fixtures = ['initial_data.json']

    def setUp(self):
        self.partner_organization = PartnerOrganization.objects.create(
            name="Partner Org 1",
            total_ct_cy=PartnerOrganization.CT_CP_AUDIT_TRIGGER_LEVEL + 1,
            last_assessment_date=datetime.date(2000, 5, 14),
        )
        self.cp = CountryProgramme.objects.create(
            name="CP 1",
            wbs="0001/A0/01",
            from_date=datetime.date(datetime.date.today().year - 1, 1, 1),
            to_date=datetime.date(datetime.date.today().year + 1, 1, 1),
        )
        year = datetime.date.today().year
        self.pca_signed1 = Agreement.objects.create(
            agreement_type=Agreement.PCA,
            partner=self.partner_organization,
            signed_by_unicef_date=datetime.date(year - 1, 1, 1),
            signed_by_partner_date=datetime.date(year - 1, 1, 1),
            country_programme=self.cp,
        )
        Agreement.objects.create(
            agreement_type=Agreement.PCA,
            partner=self.partner_organization,
            signed_by_unicef_date=datetime.date(year - 2, 1, 1),
            signed_by_partner_date=datetime.date(year - 2, 1, 1),
            country_programme=self.cp,
        )
        Agreement.objects.create(
            agreement_type=Agreement.PCA,
            partner=self.partner_organization,
            country_programme=self.cp,
        )

    def assert_min_requirements(self, programmatic_visit, spot_check):
        """common assert for minimum requirement calculation"""
        hact_min_req = self.partner_organization.hact_min_requirements
        data = {
            "programme_visits": programmatic_visit,
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
        self.partner_organization.rating = PartnerOrganization.RATING_NON_ASSESSED
        self.assertTrue(self.partner_organization.approaching_threshold_flag)

    def test_approaching_threshold_flag_false(self):
        self.partner_organization.rating = PartnerOrganization.RATING_NON_ASSESSED
        self.partner_organization.total_ct_cy = PartnerOrganization.CT_CP_AUDIT_TRIGGER_LEVEL - 1
        self.assertFalse(self.partner_organization.approaching_threshold_flag)

    def test_approaching_threshold_flag_false_moderate(self):
        self.partner_organization.rating = PartnerOrganization.RATING_MODERATE
        self.assertFalse(self.partner_organization.approaching_threshold_flag)

    def test_hact_min_requirements_ct_under_25k(self):
        self.partner_organization.total_ct_cy = 0
        hact_min_req = self.partner_organization.hact_min_requirements
        data = {
            "programme_visits": None,
            "spot_checks": None,
        }
        self.assertEqual(hact_min_req, data)

    def test_hact_min_requirements_ct_between_25k_and_50k(self):
        self.partner_organization.total_ct_cy = 44000.00
        self.assert_min_requirements(1, None)

    def test_hact_min_requirements_ct_between_25k_and_100k(self):
        self.partner_organization.total_ct_cy = 99000.00
        self.assert_min_requirements(1, 1)

    def test_hact_min_requirements_ct_between_100k_and_500k_high(self):
        self.partner_organization.total_ct_cy = 490000.00
        self.partner_organization.rating = PartnerOrganization.RATING_HIGH
        self.assert_min_requirements(3, 1)

    def test_hact_min_requirements_ct_between_100k_and_500k_significant(self):
        self.partner_organization.total_ct_cy = 490000.00
        self.partner_organization.rating = PartnerOrganization.RATING_SIGNIFICANT
        self.assert_min_requirements(3, 1)

    def test_hact_min_requirements_ct_between_100k_and_500k_moderate(self):
        self.partner_organization.total_ct_cy = 490000.00
        self.partner_organization.rating = PartnerOrganization.RATING_MODERATE
        self.assert_min_requirements(2, 1)

    def test_hact_min_requirements_ct_between_100k_and_500k_low(self):
        self.partner_organization.total_ct_cy = 490000.00
        self.partner_organization.rating = PartnerOrganization.RATING_LOW
        self.assert_min_requirements(1, 1)

    def test_hact_min_requirements_ct_over_500k_high(self):
        self.partner_organization.total_ct_cy = 510000.00
        self.partner_organization.rating = PartnerOrganization.RATING_HIGH
        self.assert_min_requirements(4, 1)

    def test_hact_min_requirements_ct_over_500k_significant(self):
        self.partner_organization.total_ct_cy = 510000.00
        self.partner_organization.rating = PartnerOrganization.RATING_SIGNIFICANT
        self.assert_min_requirements(4, 1)

    def test_hact_min_requirements_ct_over_500k_moderate(self):
        self.partner_organization.total_ct_cy = 510000.00
        self.partner_organization.rating = PartnerOrganization.RATING_MODERATE
        self.assert_min_requirements(3, 1)

    def test_hact_min_requirements_ct_over_500k_low(self):
        self.partner_organization.total_ct_cy = 510000.00
        self.partner_organization.rating = PartnerOrganization.RATING_LOW
        self.assert_min_requirements(2, 1)

    def test_planned_visits_gov(self):
        self.partner_organization.partner_type = PartnerType.GOVERNMENT
        self.partner_organization.save()
        intervention = InterventionFactory(
            agreement=self.pca_signed1,
            status=Intervention.ACTIVE
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
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['planned']['total'], 0)

    def test_planned_visits_non_gov(self):
        self.partner_organization.partner_type = PartnerType.UN_AGENCY
        self.partner_organization.save()
        intervention = InterventionFactory(
            agreement=self.pca_signed1,
            status=Intervention.ACTIVE
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
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['planned']['total'], 3)

    def test_planned_visits_non_gov_no_pv_intervention(self):
        self.partner_organization.partner_type = PartnerType.UN_AGENCY
        self.partner_organization.save()
        intervention1 = InterventionFactory(
            agreement=self.pca_signed1,
            status=Intervention.ACTIVE
        )
        intervention2 = InterventionFactory(
            agreement=self.pca_signed1,
            status=Intervention.ACTIVE
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
        PartnerOrganization.planned_visits(
            self.partner_organization
        )
        self.assertEqual(
            self.partner_organization.hact_values['programmatic_visits']['planned']['total'],
            3
        )

    def test_planned_visits_non_gov_with_pv_intervention(self):
        self.partner_organization.partner_type = PartnerType.UN_AGENCY
        self.partner_organization.save()
        intervention1 = InterventionFactory(
            agreement=self.pca_signed1,
            status=Intervention.ACTIVE
        )
        intervention2 = InterventionFactory(
            agreement=self.pca_signed1,
            status=Intervention.ACTIVE
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
        PartnerOrganization.planned_visits(
            self.partner_organization,
            pv
        )
        self.assertEqual(
            self.partner_organization.hact_values['programmatic_visits']['planned']['total'],
            3
        )

    @freeze_time("2013-05-26")
    def test_programmatic_visits_update_one(self):
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['total'], 0)
        PartnerOrganization.programmatic_visits(
            self.partner_organization,
            update_one=True
        )
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['total'], 1)
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['q1'], 0)
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['q2'], 1)
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['q3'], 0)
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['q4'], 0)

    def test_programmatic_visits_update_travel_activity(self):
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['total'], 0)
        traveller = UserFactory()
        travel = TravelFactory(
            traveler=traveller,
            status=Travel.COMPLETED,
            completed_at=datetime.datetime(datetime.datetime.today().year, 9, 1)
        )
        TravelActivityFactory(
            travels=[travel],
            primary_traveler=traveller,
            travel_type=TravelType.PROGRAMME_MONITORING,
            partner=self.partner_organization,
        )
        PartnerOrganization.programmatic_visits(self.partner_organization)
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['total'], 1)
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['q1'], 0)
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['q2'], 0)
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['q3'], 1)
        self.assertEqual(self.partner_organization.hact_values['programmatic_visits']['completed']['q4'], 0)

    @freeze_time("2013-12-26")
    def test_spot_checks_update_one(self):
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['total'], 0)
        PartnerOrganization.spot_checks(
            self.partner_organization,
            update_one=True,
        )
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['total'], 1)
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['q1'], 0)
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['q2'], 0)
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['q3'], 0)
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['q4'], 1)

    def test_spot_checks_update_travel_activity(self):
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['total'], 0)
        traveller = UserFactory()
        travel = TravelFactory(
            traveler=traveller,
            status=Travel.COMPLETED,
            completed_at=datetime.datetime(datetime.datetime.today().year, 9, 1)
        )
        TravelActivityFactory(
            travels=[travel],
            primary_traveler=traveller,
            travel_type=TravelType.SPOT_CHECK,
            partner=self.partner_organization,
        )

        SpotCheckFactory(
            partner=self.partner_organization,
            status=Engagement.FINAL,
            date_of_draft_report_to_unicef=datetime.datetime(datetime.datetime.today().year, 4, 1)
        )
        PartnerOrganization.spot_checks(self.partner_organization)
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['total'], 2)
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['q1'], 0)
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['q2'], 1)
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['q3'], 1)
        self.assertEqual(self.partner_organization.hact_values['spot_checks']['completed']['q4'], 0)

    @freeze_time("2013-12-26")
    def test_audits_completed_update_one(self):
        self.assertEqual(self.partner_organization.hact_values['audits']['completed'], 0)
        PartnerOrganization.audits_completed(
            self.partner_organization,
            update_one=True,
        )
        self.assertEqual(self.partner_organization.hact_values['audits']['completed'], 1)

    def test_audits_completed_update_travel_activity(self):
        self.assertEqual(self.partner_organization.hact_values['audits']['completed'], 0)
        AuditFactory(
            partner=self.partner_organization,
            status=Engagement.FINAL,
            date_of_draft_report_to_unicef=datetime.datetime(datetime.datetime.today().year, 4, 1)
        )
        SpecialAuditFactory(
            partner=self.partner_organization,
            status=Engagement.FINAL,
            date_of_draft_report_to_unicef=datetime.datetime(datetime.datetime.today().year, 8, 1)
        )
        PartnerOrganization.audits_completed(self.partner_organization)
        self.assertEqual(self.partner_organization.hact_values['audits']['completed'], 2)


class TestAgreementModel(TenantTestCase):
    fixtures = ['initial_data.json']

    def setUp(self):
        self.partner_organization = PartnerOrganization.objects.create(
            name="Partner Org 1",
        )
        cp = CountryProgramme.objects.create(
            name="CP 1",
            wbs="0001/A0/01",
            from_date=datetime.date(datetime.date.today().year - 1, 1, 1),
            to_date=datetime.date(datetime.date.today().year + 1, 1, 1),
        )
        self.agreement = Agreement.objects.create(
            agreement_type=Agreement.PCA,
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
        cp = CountryProgramme.objects.create(
            name="CP 1",
            wbs="0001/A0/01",
            from_date=datetime.date(datetime.date.today().year - 1, 1, 1),
            to_date=datetime.date(datetime.date.today().year + 1, 1, 1),
        )
        agreement = Agreement.objects.create(
            agreement_type=Agreement.PCA,
            partner=self.partner_organization,
            country_programme=cp,
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
