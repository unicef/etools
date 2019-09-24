from datetime import timedelta

import factory
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from unicef_locations.tests.factories import LocationFactory

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.field_monitoring.planning.tests.factories import MonitoringActivityFactory
from etools.applications.field_monitoring.tests.factories import UserFactory
from etools.applications.partners.tests.factories import PartnerFactory, InterventionFactory
from etools.applications.reports.models import ResultType
from etools.applications.reports.tests.factories import ResultFactory


class OverallViewTestCase(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = UserFactory(unicef_user=True)

        cls.activities = MonitoringActivityFactory.create_batch(2, status=MonitoringActivity.STATUSES.completed)
        cls.failed_activity = MonitoringActivityFactory(status=MonitoringActivity.STATUSES.cancelled)

    def test_response(self):
        with self.assertNumQueries(1):
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

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['id'], self.partner.id)
        self.assertEqual(response.data[0]['visits_count'], 2)
        self.assertEqual([v['id'] for v in response.data[0]['visits']], [a.id for a in self.activities])
        self.assertEqual(response.data[1]['id'], self.second_partner.id)
        self.assertEqual(response.data[1]['visits_count'], 1)
        self.assertEqual(response.data[1]['visits'][0]['id'], self.activities[1].id)


class PartnersCoverageViewTestCase(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory(unicef_user=True)

    def test_response(self):
        partner = PartnerFactory()
        PartnerFactory()  # no activities, should be hidden

        MonitoringActivityFactory(
            partners=[partner], status=MonitoringActivity.STATUSES.completed,
            end_date=(timezone.now() - timedelta(days=15)).date()
        ),
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
        ),

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

    def test_response(self):
        country = LocationFactory(gateway__admin_level=0)
        first_location = LocationFactory(parent=country)
        second_location = LocationFactory(parent=country)
        LocationFactory(parent=first_location)  # hidden

        MonitoringActivityFactory.create_batch(
            size=2, location=first_location, status=MonitoringActivity.STATUSES.completed
        )
        MonitoringActivityFactory(location=first_location, status=MonitoringActivity.STATUSES.draft)

        with self.assertNumQueries(1):
            response = self.forced_auth_req(
                'get',
                reverse('field_monitoring_analyze:coverage-geographic'),
                user=self.user
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['id'], first_location.id)
        self.assertEqual(response.data[0]['completed_visits'], 2)
        self.assertEqual(response.data[1]['id'], second_location.id)
        self.assertEqual(response.data[1]['completed_visits'], 0)
