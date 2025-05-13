import unittest.mock as mock
from datetime import date

from django.contrib.auth.models import Group
from django.test import override_settings

from freezegun import freeze_time

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.last_mile.admin_panel.constants import *  # NOQA
from etools.applications.last_mile.admin_panel.services.MonthlyUsersReportGenerator import MonthlyUsersReportGenerator
from etools.applications.last_mile.admin_panel.services.MonthlyUsersReportNotificator import (
    MonthlyUsersReportNotificator,
)
from etools.applications.last_mile.models import Profile
from etools.applications.last_mile.tests.factories import LastMileProfileFactory
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.users.tests.factories import CountryFactory, UserPermissionFactory

MOCK_REPORT_GENERATOR_PATH = "etools.applications.last_mile.admin_panel.services.MonthlyUsersReportNotificator.MonthlyUsersReportGenerator"
MOCK_SEND_NOTIFICATION_PATH = "etools.applications.last_mile.admin_panel.services.MonthlyUsersReportNotificator.send_notification"
current_test_date_str = "2023-07-15"


@override_settings(DEFAULT_FROM_EMAIL="test_sender@example.com")
class TestMonthlyUserReports(BaseTenantTestCase):
    fixtures = ("poi_type.json", "unicef_warehouse.json", "groups.json")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.partner = PartnerFactory(organization=OrganizationFactory(name="Partner"))
        cls.organization = OrganizationFactory(name="Update Organization")
        cls.country1 = CountryFactory(schema_name="test", name="Country Test 1")
        cls.country2 = CountryFactory(schema_name="test", name="Country Test 2")

        try:
            cls.report_group = Group.objects.get(name="LMSM User Creation Report")
        except Group.DoesNotExist:
            cls.report_group = Group.objects.create(name="LMSM User Creation Report")
        cls.user_c1_active_report_group1 = UserPermissionFactory(
            email="user_c1_active_report1@example.com",
            realms__country=cls.country1,
            realms__data=["LMSM User Creation Report"],
            realms__is_active=True,
            profile__organization=cls.partner.organization,
            perms=[USER_ADMIN_PANEL_PERMISSION],
        )
        cls.user_c1_active_report_group2 = UserPermissionFactory(
            email="user_c1_active_report2@example.com",
            realms__country=cls.country1,
            realms__data=["LMSM User Creation Report"],
            realms__is_active=True,
            profile__organization=cls.partner.organization,
            perms=[USER_ADMIN_PANEL_PERMISSION],
        )
        cls.user_c1_inactive_report_group = UserPermissionFactory(
            email="user_c1_inactive_report@example.com",
            realms__country=cls.country1,
            realms__data=["LMSM User Creation Report"],
            realms__is_active=False,  # Inactive
            profile__organization=cls.partner.organization,
            perms=[USER_ADMIN_PANEL_PERMISSION],
        )
        other_group, _ = Group.objects.get_or_create(name="Other Group")
        cls.user_c1_active_other_group = UserPermissionFactory(
            email="user_c1_active_othergroup@example.com",
            realms__country=cls.country1,
            realms__data=["Other Group"],
            realms__is_active=True,
            profile__organization=cls.partner.organization,
            perms=[USER_ADMIN_PANEL_PERMISSION],
        )

        cls.user_c2_active_report_group1 = UserPermissionFactory(
            email="user_c2_active_report1@example.com",
            realms__country=cls.country2,
            realms__data=["LMSM User Creation Report"],
            realms__is_active=True,
            profile__organization=cls.partner.organization,
            perms=[USER_ADMIN_PANEL_PERMISSION],
        )

        cls.current_test_date = date(2023, 7, 15)

        cls.last_month_start = date(2023, 6, 1)
        cls.last_month_mid = date(2023, 6, 15)
        cls.last_month_end = date(2023, 6, 30)

        cls.this_month_start = date(2023, 7, 1)

        cls.profile_c1_last_month1 = LastMileProfileFactory(
            user=cls.user_c1_active_report_group1, created_on=cls.last_month_mid
        )
        cls.profile_c1_last_month2 = LastMileProfileFactory(
            user=cls.user_c1_inactive_report_group, created_on=cls.last_month_start
        )
        cls.profile_c1_this_month = LastMileProfileFactory(
            user=cls.user_c1_active_report_group2, created_on=cls.this_month_start
        )

        cls.profile_c2_last_month = LastMileProfileFactory(
            user=cls.user_c2_active_report_group1, created_on=cls.last_month_end
        )

        cls.profile_c1_other_group_last_month = LastMileProfileFactory(
            user=cls.user_c1_active_other_group, created_on=cls.last_month_mid
        )

        cls.notificator = MonthlyUsersReportNotificator()
        cls.generator = MonthlyUsersReportGenerator()

    @freeze_time("2023-01-15")
    def test_generator_no_profiles_in_last_month(self):
        Profile.objects.filter(
            created_on__year=2022,
            created_on__month=12,
            user__realms__country__schema_name="test",
        ).delete()

        generated_data = self.generator.generate_data_for_monthly_users_created_report(
            "test"
        )
        self.assertEqual(len(generated_data), 0)

    @freeze_time(current_test_date_str)
    def test_generator_non_existent_tenant(self):
        generated_data = self.generator.generate_data_for_monthly_users_created_report(
            "non_existent_tenant"
        )
        self.assertEqual(len(generated_data), 0)

    @freeze_time(current_test_date_str)
    @mock.patch(MOCK_SEND_NOTIFICATION_PATH)
    @mock.patch(
        f"{MOCK_REPORT_GENERATOR_PATH}.generate_data_for_monthly_users_created_report"
    )
    def test_notificator_sends_email_correct_recipients_tenant1(
        self, mock_generate_data, mock_send_notification
    ):
        mock_monthly_data = [
            {"id": 1, "info": "Profile 1"},
            {"id": 2, "info": "Profile 2"},
        ]
        mock_generate_data.return_value = mock_monthly_data

        self.notificator.send_email_notification("test")

        mock_generate_data.assert_called_once_with("test")
        mock_send_notification.assert_called_once()

        args, kwargs = mock_send_notification.call_args

        expected_recipients = sorted(
            [
                self.user_c1_active_report_group1.email,
                self.user_c1_active_report_group2.email,
                self.user_c1_inactive_report_group.email,
                self.user_c2_active_report_group1.email,
            ]
        )
        self.assertEqual(sorted(list(kwargs["recipients"])), expected_recipients)
        self.assertEqual(len(kwargs["recipients"]), 4)

        self.assertEqual(kwargs["from_address"], "no-reply@unicef.org")
        self.assertEqual(kwargs["subject"], "LMSM : Monthly User Creation Report")
        self.assertEqual(kwargs["html_content_filename"], "emails/last_mile_users.html")
        self.assertEqual(kwargs["context"], {"monthly_data": mock_monthly_data})

    @freeze_time(current_test_date_str)
    @mock.patch(MOCK_SEND_NOTIFICATION_PATH)
    @mock.patch(
        f"{MOCK_REPORT_GENERATOR_PATH}.generate_data_for_monthly_users_created_report"
    )
    def test_notificator_sends_email_correct_recipients_tenant2(
        self, mock_generate_data, mock_send_notification
    ):
        mock_monthly_data = [{"id": 3, "info": "Profile 3"}]
        mock_generate_data.return_value = mock_monthly_data

        self.notificator.send_email_notification("test")

        mock_generate_data.assert_called_once_with("test")
        mock_send_notification.assert_called_once()

        args, kwargs = mock_send_notification.call_args

        expected_recipients = sorted(
            [
                self.user_c1_active_report_group1.email,
                self.user_c1_active_report_group2.email,
                self.user_c1_inactive_report_group.email,
                self.user_c2_active_report_group1.email,
            ]
        )
        self.assertEqual(sorted(list(kwargs["recipients"])), expected_recipients)
        self.assertEqual(len(kwargs["recipients"]), 4)

        self.assertEqual(kwargs["context"], {"monthly_data": mock_monthly_data})

    @freeze_time(current_test_date_str)
    @mock.patch(MOCK_SEND_NOTIFICATION_PATH)
    @mock.patch(
        f"{MOCK_REPORT_GENERATOR_PATH}.generate_data_for_monthly_users_created_report"
    )
    def test_notificator_no_recipients_for_tenant(
        self, mock_generate_data, mock_send_notification
    ):
        mock_monthly_data = [{"id": 1}]
        mock_generate_data.return_value = mock_monthly_data

        self.notificator.send_email_notification("non_existent_tenant")

        mock_generate_data.assert_called_once_with("non_existent_tenant")
        mock_send_notification.assert_called_once()

        args, kwargs = mock_send_notification.call_args
        self.assertEqual(list(kwargs["recipients"]), [])

    @freeze_time(current_test_date_str)
    @mock.patch(MOCK_SEND_NOTIFICATION_PATH)
    @mock.patch(
        f"{MOCK_REPORT_GENERATOR_PATH}.generate_data_for_monthly_users_created_report"
    )
    def test_notificator_report_generator_returns_empty_data(
        self, mock_generate_data, mock_send_notification
    ):
        mock_generate_data.return_value = []  # Generator returns empty list

        self.notificator.send_email_notification("test")

        mock_generate_data.assert_called_once_with("test")
        mock_send_notification.assert_called_once()

        args, kwargs = mock_send_notification.call_args
        self.assertEqual(kwargs["context"], {"monthly_data": []})

        expected_recipients = sorted(
            [
                self.user_c1_active_report_group1.email,
                self.user_c1_active_report_group2.email,
                self.user_c1_inactive_report_group.email,
                self.user_c2_active_report_group1.email,
            ]
        )
        self.assertEqual(sorted(list(kwargs["recipients"])), expected_recipients)

    @freeze_time(current_test_date_str)
    @mock.patch(MOCK_SEND_NOTIFICATION_PATH)
    @mock.patch(
        f"{MOCK_REPORT_GENERATOR_PATH}.generate_data_for_monthly_users_created_report"
    )
    def test_notificator_distinct_recipients(
        self, mock_generate_data, mock_send_notification
    ):
        mock_monthly_data = [{"id": 1}]
        mock_generate_data.return_value = mock_monthly_data

        self.notificator.send_email_notification("test")

        mock_send_notification.assert_called_once()
        args, kwargs = mock_send_notification.call_args
        recipients = kwargs["recipients"]

        self.assertEqual(len(recipients), len(set(recipients)))

        expected_recipients = sorted(
            [
                self.user_c1_active_report_group1.email,
                self.user_c1_active_report_group2.email,
                self.user_c1_inactive_report_group.email,
                self.user_c2_active_report_group1.email,
            ]
        )
        self.assertEqual(sorted(list(recipients)), expected_recipients)
