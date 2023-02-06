import datetime
from unittest.mock import Mock, patch

from django.conf import settings
from django.core.management import call_command
from django.utils import timezone

from dateutil.relativedelta import relativedelta
from unicef_locations.tests.factories import LocationFactory

from etools.applications.attachments.tests.factories import AttachmentFileTypeFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.funds.tests.factories import FundsReservationHeaderFactory
from etools.applications.partners import utils
from etools.applications.partners.models import Agreement, Intervention, InterventionResultLink
from etools.applications.partners.tests.factories import AgreementFactory, InterventionFactory, PartnerFactory
from etools.applications.reports.models import AppliedIndicator, IndicatorBlueprint, LowerResult, ResultType
from etools.applications.reports.tests.factories import (
    CountryProgrammeFactory,
    ReportingRequirementFactory,
    ResultFactory,
)
from etools.applications.users.tests.factories import GroupFactory, UserFactory


def setup_intervention_test_data(test_case, include_results_and_indicators=False):
    today = datetime.date.today()
    test_case.unicef_staff = UserFactory(is_staff=True)
    test_case.partnership_manager_user = UserFactory(is_staff=True)
    test_case.partnership_manager_user.groups.add(GroupFactory())
    test_case.partner = PartnerFactory(name='Partner 1', vendor_number="VP1")
    test_case.partner1 = PartnerFactory(name='Partner 2')
    test_case.agreement = AgreementFactory(partner=test_case.partner, signed_by_unicef_date=datetime.date.today())

    test_case.active_agreement = AgreementFactory(
        partner=test_case.partner1,
        status='active',
        signed_by_unicef_date=datetime.date.today(),
        signed_by_partner_date=datetime.date.today()
    )

    test_case.intervention = InterventionFactory(
        agreement=test_case.agreement,
        title='Intervention 1',
        status=Intervention.DRAFT,
    )
    test_case.intervention.unicef_focal_points.add(test_case.partnership_manager_user)
    test_case.intervention_2 = InterventionFactory(
        agreement=test_case.agreement,
        title='Intervention 2',
        document_type=Intervention.PD,
        status=Intervention.DRAFT,
    )
    test_case.intervention_2.unicef_focal_points.add(test_case.partnership_manager_user)
    test_case.active_intervention = InterventionFactory(
        agreement=test_case.active_agreement,
        title='Active Intervention',
        document_type=Intervention.PD,
        start=today - datetime.timedelta(days=1),
        end=today + datetime.timedelta(days=90),
        status=Intervention.ACTIVE,
        date_sent_to_partner=today - datetime.timedelta(days=1),
        signed_by_unicef_date=today - datetime.timedelta(days=1),
        signed_by_partner_date=today - datetime.timedelta(days=1),
        unicef_signatory=test_case.unicef_staff,
        partner_authorized_officer_signatory=test_case.partner1.staff_members.all().first()
    )
    test_case.active_intervention.unicef_focal_points.add(test_case.partnership_manager_user)
    test_case.reporting_requirement = ReportingRequirementFactory(intervention=test_case.active_intervention)
    test_case.result_type = ResultType.objects.get_or_create(name=ResultType.OUTPUT)[0]
    test_case.result = ResultFactory(result_type=test_case.result_type)

    test_case.management_budget = test_case.intervention.management_budgets
    test_case.partnership_budget = test_case.intervention.planned_budget

    # set up two frs not connected to any interventions
    test_case.fr_1 = FundsReservationHeaderFactory(intervention=None, currency='USD')
    test_case.fr_2 = FundsReservationHeaderFactory(intervention=None, currency='USD')

    if include_results_and_indicators:
        # setup additional inicator/results
        test_case.result = ResultFactory(name='A Result')
        test_case.result_link = InterventionResultLink.objects.create(
            intervention=test_case.active_intervention, cp_output=test_case.result)
        test_case.lower_result = LowerResult.objects.create(result_link=test_case.result_link,
                                                            name='Lower Result 1')
        test_case.indicator_blueprint = IndicatorBlueprint.objects.create(
            title='The Blueprint'
        )
        test_case.applied_indicator = AppliedIndicator.objects.create(
            indicator=test_case.indicator_blueprint,
            lower_result=test_case.lower_result,
        )
        test_case.applied_indicator.locations.add(LocationFactory(
            name='A Location',
            p_code='a-p-code')
        )
        test_case.disaggregation = test_case.applied_indicator.disaggregation.create(name='A Disaggregation')

    test_case.file_type_attachment = AttachmentFileTypeFactory(
        code="partners_intervention_attachments"
    )
    test_case.file_type_prc = AttachmentFileTypeFactory(
        code="partners_intervention_prc_review"
    )
    test_case.file_type_pd = AttachmentFileTypeFactory(
        code="partners_intervention_signed_pd"
    )


class TestSendPCARequiredNotification(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("update_notifications")
        cls.send_path = "etools.applications.partners.utils.send_notification_with_template"

    def setUp(self):
        self.lead_date = datetime.date.today() + datetime.timedelta(
            days=settings.PCA_REQUIRED_NOTIFICATION_LEAD
        )

    def test_direct_cp(self):
        cp = CountryProgrammeFactory(to_date=self.lead_date)
        intervention = InterventionFactory(
            document_type=Intervention.PD,
            end=self.lead_date + datetime.timedelta(days=10),
        )
        intervention.country_programmes.add(cp)
        mock_send = Mock()
        with patch(self.send_path, mock_send):
            utils.send_pca_required_notifications()
        self.assertEqual(mock_send.call_count, 1)

    def test_agreement_cp(self):
        cp = CountryProgrammeFactory(to_date=self.lead_date)
        agreement = AgreementFactory(country_programme=cp)
        InterventionFactory(
            document_type=Intervention.PD,
            end=self.lead_date + datetime.timedelta(days=10),
            agreement=agreement,
        )
        mock_send = Mock()
        with patch(self.send_path, mock_send):
            utils.send_pca_required_notifications()
        self.assertEqual(mock_send.call_count, 1)


class TestSendPCAMissingNotification(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("update_notifications")
        cls.send_path = "etools.applications.partners.utils.send_notification_with_template"

    def test_cp_current(self):
        date_past = datetime.date.today() - datetime.timedelta(days=10)
        date_future = datetime.date.today() + datetime.timedelta(days=10)
        cp = CountryProgrammeFactory(
            from_date=date_past,
            to_date=date_future,
        )
        agreement = AgreementFactory(
            agreement_type=Agreement.PCA,
            country_programme=cp,
        )
        InterventionFactory(
            document_type=Intervention.PD,
            start=date_past,
            end=datetime.date.today(),
            agreement=agreement,
        )
        mock_send = Mock()
        with patch(self.send_path, mock_send):
            utils.send_pca_missing_notifications()
        self.assertEqual(mock_send.call_count, 0)

    def test_cp_previous_pca_missing(self):
        date_past = datetime.date.today() - datetime.timedelta(days=10)
        date_future = datetime.date.today() + datetime.timedelta(days=10)
        partner = PartnerFactory()
        cp = CountryProgrammeFactory(
            from_date=date_past,
            to_date=datetime.date.today(),
        )
        agreement = AgreementFactory(
            partner=partner,
            agreement_type=Agreement.PCA,
            country_programme=cp,
        )
        InterventionFactory(
            document_type=Intervention.PD,
            start=date_past + datetime.timedelta(days=1),
            end=date_future,
            agreement=agreement,
        )
        mock_send = Mock()
        with patch(self.send_path, mock_send):
            utils.send_pca_missing_notifications()
        self.assertEqual(mock_send.call_count, 1)

    def test_cp_previous(self):
        date_past = datetime.date.today() - datetime.timedelta(days=10)
        date_future = datetime.date.today() + datetime.timedelta(days=10)
        partner = PartnerFactory()
        cp_previous = CountryProgrammeFactory(
            from_date=date_past,
            to_date=datetime.date.today(),
        )
        agreement_previous = AgreementFactory(
            partner=partner,
            agreement_type=Agreement.PCA,
            country_programme=cp_previous,
        )
        cp = CountryProgrammeFactory(
            from_date=datetime.date.today() + datetime.timedelta(days=1),
            to_date=date_future,
        )
        AgreementFactory(
            partner=partner,
            agreement_type=Agreement.PCA,
            country_programme=cp,
        )
        InterventionFactory(
            document_type=Intervention.PD,
            start=date_past + datetime.timedelta(days=1),
            end=datetime.date.today() + datetime.timedelta(days=1),
            agreement=agreement_previous,
        )
        mock_send = Mock()
        with patch(self.send_path, mock_send):
            utils.send_pca_missing_notifications()
        self.assertEqual(mock_send.call_count, 0)


class TestSendInterventionDraftNotification(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("update_notifications")
        cls.send_path = "etools.applications.partners.utils.send_notification_with_template"

    def test_send(self):
        intervention = InterventionFactory(status=Intervention.DRAFT)
        tz = timezone.get_default_timezone()
        intervention.created = datetime.datetime(2018, 1, 1, 12, 55, 12, 12345, tzinfo=tz)
        intervention.save()
        mock_send = Mock()
        with patch(self.send_path, mock_send):
            utils.send_intervention_draft_notification()
        self.assertEqual(mock_send.call_count, 1)

    def test_send_not_week_old(self):
        InterventionFactory(status=Intervention.DRAFT)
        mock_send = Mock()
        with patch(self.send_path, mock_send):
            utils.send_intervention_draft_notification()
        self.assertEqual(mock_send.call_count, 0)

    def test_send_not_draft(self):
        intervention = InterventionFactory(status=Intervention.SIGNED)
        self.assertTrue(intervention.status != Intervention.DRAFT)
        self.assertFalse(Intervention.objects.filter(status=Intervention.DRAFT).exists())
        mock_send = Mock()
        with patch(self.send_path, mock_send):
            utils.send_intervention_draft_notification()
        self.assertEqual(mock_send.call_count, 0)


class TestSendInterventionPastStartNotification(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("update_notifications")
        cls.send_path = "etools.applications.partners.utils.send_notification_with_template"

    def test_send(self):
        intervention = InterventionFactory(
            status=Intervention.SIGNED,
            start=datetime.date.today() - datetime.timedelta(days=2),
        )
        FundsReservationHeaderFactory(intervention=intervention)
        mock_send = Mock()
        with patch(self.send_path, mock_send):
            utils.send_intervention_past_start_notification()
        self.assertEqual(mock_send.call_count, 1)

    def test_send_not_signed(self):
        intervention = InterventionFactory(
            status=Intervention.DRAFT,
            start=datetime.date.today() - datetime.timedelta(days=2),
        )
        FundsReservationHeaderFactory(intervention=intervention)
        mock_send = Mock()
        with patch(self.send_path, mock_send):
            utils.send_intervention_past_start_notification()
        self.assertEqual(mock_send.call_count, 0)

    def test_send_not_past(self):
        InterventionFactory(
            status=Intervention.SIGNED,
            start=datetime.date.today() + datetime.timedelta(days=2),
        )
        mock_send = Mock()
        with patch(self.send_path, mock_send):
            utils.send_intervention_past_start_notification()
        self.assertEqual(mock_send.call_count, 0)

    def test_send_has_no_frs(self):
        InterventionFactory(
            status=Intervention.SIGNED,
            start=datetime.date.today() - datetime.timedelta(days=2),
        )
        mock_send = Mock()
        with patch(self.send_path, mock_send):
            utils.send_intervention_past_start_notification()
        self.assertEqual(mock_send.call_count, 0)


class TestGetQuartersRange(BaseTenantTestCase):
    def test_missing_dates(self):
        self.assertEqual(
            utils.get_quarters_range(None, datetime.date.today()),
            [],
        )
        self.assertEqual(
            utils.get_quarters_range(datetime.date.today(), None),
            [],
        )

    def test_start_after_end(self):
        today = datetime.date.today()
        self.assertEqual(
            utils.get_quarters_range(today + relativedelta(months=2), today),
            [],
        )

    def test_middle_of_quarter(self):
        start = datetime.date(2001, 1, 1)
        end = datetime.date(2001, 5, 27)
        self.assertEqual(
            utils.get_quarters_range(start, end),
            [
                utils.Quarter(1, start=start, end=datetime.date(2001, 3, 31)),
                utils.Quarter(2, start=datetime.date(2001, 4, 1), end=end),
            ],
        )

    def test_end_of_quarter(self):
        start = datetime.date(2001, 1, 1)
        self.assertEqual(
            utils.get_quarters_range(start, start + relativedelta(months=15)),
            [
                utils.Quarter(1, start=start, end=datetime.date(2001, 3, 31)),
                utils.Quarter(
                    2,
                    start=datetime.date(2001, 4, 1),
                    end=datetime.date(2001, 6, 30),
                ),
                utils.Quarter(
                    3,
                    start=datetime.date(2001, 7, 1),
                    end=datetime.date(2001, 9, 30),
                ),
                utils.Quarter(
                    4,
                    start=datetime.date(2001, 10, 1),
                    end=datetime.date(2001, 12, 31),
                ),
                utils.Quarter(
                    5,
                    start=datetime.date(2002, 1, 1),
                    end=datetime.date(2002, 3, 31),
                ),
            ],
        )
