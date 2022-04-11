from datetime import timedelta

from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

import factory
from rest_framework import status
from unicef_locations.tests.factories import LocationFactory

from etools.applications.action_points.models import ActionPoint
from etools.applications.action_points.tests.factories import ActionPointFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.fm_settings.models import LogIssue
from etools.applications.field_monitoring.fm_settings.tests.factories import LogIssueFactory
from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.field_monitoring.planning.tests.factories import MonitoringActivityFactory
from etools.applications.field_monitoring.tests.factories import UserFactory
from etools.applications.partners.tests.factories import (
    InterventionFactory,
    PartnerFactory,
    PartnerPlannedVisitsFactory,
)
from etools.applications.reports.models import ResultType
from etools.applications.reports.tests.factories import ResultFactory, SectionFactory
from etools.libraries.pythonlib.datetime import get_current_year


class OverallViewTestCase(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = UserFactory(unicef_user=True)

        cls.activities = MonitoringActivityFactory.create_batch(2, status=MonitoringActivity.STATUSES.completed)
        cls.failed_activity = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.cancelled)

    def test_response(self):
        with self.assertNumQueries(2):
            response = self.forced_auth_req(
                'get',
                reverse('field_monitoring_analyze:overall'),
                user=self.user
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['visits_completed'], 2)
        self.assertEqual(response.data['visits_planned'], 0)


class HACTViewTestCase(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = UserFactory(unicef_user=True)

        cls.partner = PartnerFactory()
        cls.second_partner = PartnerFactory()
        cls.activities = [
            MonitoringActivityFactory(partners=[cls.partner], status=MonitoringActivity.STATUSES.completed),
            MonitoringActivityFactory(partners=[cls.partner, cls.second_partner],
                                      status=MonitoringActivity.STATUSES.completed),
        ]
        cls.draft_activity = MonitoringActivityFactory(partners=[cls.partner], status=MonitoringActivity.STATUSES.draft)

    def test_response(self):

        with self.assertNumQueries(4):
            response = self.forced_auth_req(
                'get',
                reverse('field_monitoring_analyze:hact'),
                user=self.user
            )

        # TODO: improve these tests
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['id'], self.partner.id)
        self.assertEqual(response.data[0]['visits_count'], 0)
        self.assertEqual([v['id'] for v in response.data[0]['visits']], [a.id for a in self.activities])
        self.assertEqual(response.data[1]['id'], self.second_partner.id)
        self.assertEqual(response.data[1]['visits_count'], 0)
        self.assertEqual(response.data[1]['visits'][0]['id'], self.activities[1].id)


class PartnersCoverageViewTestCase(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory(unicef_user=True)

    def test_response(self):
        partner = PartnerFactory()
        PartnerFactory()  # no activities, should be hidden
        PartnerPlannedVisitsFactory(
            partner=partner,
            year=get_current_year(),
            programmatic_q1=1,
            programmatic_q2=2,
            programmatic_q3=3,
            programmatic_q4=4,
        )
        PartnerPlannedVisitsFactory(
            partner=partner,
            year=get_current_year() - 1,
        )

        MonitoringActivityFactory(
            partners=[partner], status=MonitoringActivity.STATUSES.completed,
            end_date=(timezone.now() - timedelta(days=15)).date()
        )
        MonitoringActivityFactory(partners=[partner])

        with self.assertNumQueries(1):
            response = self.forced_auth_req(
                'get',
                reverse('field_monitoring_analyze:coverage-partners'),
                user=self.user
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], partner.id)
        self.assertEqual(response.data[0]['completed_visits'], 1)
        self.assertEqual(response.data[0]['planned_visits'], 0)
        self.assertEqual(response.data[0]['days_since_visit'], 15)
        self.assertEqual(response.data[0]['minimum_required_visits'], partner.min_req_programme_visits)


class InterventionsCoverageViewTestCase(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory(unicef_user=True)

    def test_response(self):
        intervention = InterventionFactory()
        InterventionFactory()  # no activities, should be hidden

        MonitoringActivityFactory.create_batch(
            size=4, interventions=[intervention], status=MonitoringActivity.STATUSES.completed,
            end_date=factory.Iterator((timezone.now() - timedelta(days=i)).date() for i in [30, 26, 21, 12])
        ),

        with self.assertNumQueries(1):
            response = self.forced_auth_req(
                'get',
                reverse('field_monitoring_analyze:coverage-interventions'),
                user=self.user
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], intervention.id)
        self.assertEqual(response.data[0]['days_since_visit'], 12)
        self.assertEqual(response.data[0]['avg_days_between_visits'], 6)


class CPOutputsCoverageViewTestCase(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory(unicef_user=True)

    def test_response(self):
        output = ResultFactory(result_type__name=ResultType.OUTPUT)
        ResultFactory(result_type__name=ResultType.OUTPUT)  # no activities, should be hidden

        MonitoringActivityFactory.create_batch(
            size=4, cp_outputs=[output], status=MonitoringActivity.STATUSES.completed,
            end_date=factory.Iterator((timezone.now() - timedelta(days=i)).date() for i in [30, 26, 21, 12])
        )

        with self.assertNumQueries(1):
            response = self.forced_auth_req(
                'get',
                reverse('field_monitoring_analyze:coverage-cp_outputs'),
                user=self.user
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], output.id)
        self.assertEqual(response.data[0]['days_since_visit'], 12)
        self.assertEqual(response.data[0]['avg_days_between_visits'], 6)


class GeographicCoverageViewTestCase(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory(unicef_user=True)

        cls.country = LocationFactory(admin_level=0)
        cls.first_location = LocationFactory(parent=cls.country)
        cls.second_location = LocationFactory(parent=cls.country)
        LocationFactory(parent=cls.first_location)  # hidden

        cls.section_education = SectionFactory(name='Education')
        cls.section_protection = SectionFactory(name='Protection')

        cls.protection_activities = MonitoringActivityFactory.create_batch(
            size=2, location=cls.first_location, status=MonitoringActivity.STATUSES.completed,
            sections=[cls.section_protection],
        )
        cls.education_activities = MonitoringActivityFactory.create_batch(
            size=3, location=cls.first_location, status=MonitoringActivity.STATUSES.completed,
            sections=[cls.section_education],
        )

        # one activity with both sections
        cls.protection_activities[0].sections.add(cls.section_education)
        cls.education_activities.append(cls.protection_activities[0])

        cls.no_section_activity = MonitoringActivityFactory(
            location=cls.first_location, status=MonitoringActivity.STATUSES.completed
        )

        cls.draft_activity = MonitoringActivityFactory(
            location=cls.first_location, status=MonitoringActivity.STATUSES.draft
        )

        cls.sublocation_activity = MonitoringActivityFactory(
            location__parent=cls.second_location, status=MonitoringActivity.STATUSES.completed
        )

    def test_response(self):
        with self.assertNumQueries(1):
            response = self.forced_auth_req(
                'get',
                reverse('field_monitoring_analyze:coverage-geographic'),
                user=self.user
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['id'], self.first_location.id)
        self.assertEqual(response.data[0]['completed_visits'], 6)
        self.assertEqual(response.data[1]['id'], self.second_location.id)
        self.assertEqual(response.data[1]['completed_visits'], 1)

    def test_filter_by_section(self):
        with self.assertNumQueries(1):
            response = self.forced_auth_req(
                'get',
                reverse('field_monitoring_analyze:coverage-geographic'),
                user=self.user,
                data={'sections__in': str(self.section_protection.id)}
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['id'], self.first_location.id)
        self.assertEqual(response.data[0]['completed_visits'], 2)

    def test_filter_by_multiple_sections(self):
        with self.assertNumQueries(1):
            response = self.forced_auth_req(
                'get',
                reverse('field_monitoring_analyze:coverage-geographic'),
                user=self.user,
                data={'sections__in': ','.join(map(str, [self.section_protection.id, self.section_education.id]))}
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['id'], self.first_location.id)
        self.assertEqual(response.data[0]['completed_visits'], 5)


class IssuesPartnersViewTestCase(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory(unicef_user=True)
        call_command('update_notifications')

    def test_response(self):
        partner = PartnerFactory()
        PartnerFactory()

        LogIssueFactory.create_batch(size=2, partner=partner, status=LogIssue.STATUS_CHOICES.new)
        LogIssueFactory(partner=partner, status=LogIssue.STATUS_CHOICES.past)

        ActionPointFactory.create_batch(size=3, partner=partner, status=ActionPoint.STATUS_OPEN)
        ActionPointFactory(partner=partner, status=ActionPoint.STATUS_COMPLETED)

        with self.assertNumQueries(1):
            response = self.forced_auth_req(
                'get',
                reverse('field_monitoring_analyze:issues-partners'),
                user=self.user
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], partner.id)
        self.assertEqual(response.data[0]['log_issues_count'], 2)
        self.assertEqual(response.data[0]['action_points_count'], 3)


class IssuesCPOutputsViewTestCase(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory(unicef_user=True)
        call_command('update_notifications')

    def test_response(self):
        cp_output = ResultFactory(result_type__name=ResultType.OUTPUT)
        ResultFactory(result_type__name=ResultType.OUTPUT)

        LogIssueFactory.create_batch(size=3, cp_output=cp_output, status=LogIssue.STATUS_CHOICES.new)
        LogIssueFactory(cp_output=cp_output, status=LogIssue.STATUS_CHOICES.past)

        ActionPointFactory.create_batch(size=2, cp_output=cp_output, status=ActionPoint.STATUS_OPEN)
        ActionPointFactory(cp_output=cp_output, status=ActionPoint.STATUS_COMPLETED)

        with self.assertNumQueries(1):
            response = self.forced_auth_req(
                'get',
                reverse('field_monitoring_analyze:issues-cp_outputs'),
                user=self.user
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], cp_output.id)
        self.assertEqual(response.data[0]['log_issues_count'], 3)
        self.assertEqual(response.data[0]['action_points_count'], 2)


class IssuesLocationsViewTestCase(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory(unicef_user=True)
        call_command('update_notifications')

    def test_response(self):
        location = LocationFactory()
        LocationFactory()

        LogIssueFactory.create_batch(size=4, location=location, status=LogIssue.STATUS_CHOICES.new)
        LogIssueFactory(location=location, status=LogIssue.STATUS_CHOICES.past)

        ActionPointFactory.create_batch(size=3, location=location, status=ActionPoint.STATUS_OPEN)
        ActionPointFactory(location=location, status=ActionPoint.STATUS_COMPLETED)

        with self.assertNumQueries(1):
            response = self.forced_auth_req(
                'get',
                reverse('field_monitoring_analyze:issues-locations'),
                user=self.user
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], location.id)
        self.assertEqual(response.data[0]['log_issues_count'], 4)
        self.assertEqual(response.data[0]['action_points_count'], 3)
