from django.test import override_settings
from django.urls import reverse

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.travel.models import Trip
from etools.applications.travel.tests.factories import TripFactory
from etools.applications.users.tests.factories import GroupFactory, RealmFactory, UserFactory


@override_settings(RESTRICTED_ADMIN=False)
class TestRssAdminTripsApi(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.admin_user = UserFactory(is_staff=True)
        cls.supervisor1 = UserFactory()
        cls.supervisor2 = UserFactory()
        cls.traveller = UserFactory()

    def test_change_approver_success_when_submitted(self):
        trip = TripFactory(traveller=self.traveller, supervisor=self.supervisor1)
        trip.status = Trip.STATUS_SUBMITTED
        trip.save()

        url = reverse('rss_admin:rss-admin-trips-change-approver', kwargs={'pk': trip.pk})
        resp = self.forced_auth_req('patch', url, user=self.admin_user, data={'supervisor_id': self.supervisor2.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        trip.refresh_from_db()
        self.assertEqual(trip.supervisor_id, self.supervisor2.id)

    def test_change_approver_fails_when_not_submitted(self):
        trip = TripFactory(traveller=self.traveller, supervisor=self.supervisor1)
        trip.status = Trip.STATUS_DRAFT
        trip.save()

        url = reverse('rss_admin:rss-admin-trips-change-approver', kwargs={'pk': trip.pk})
        resp = self.forced_auth_req('patch', url, user=self.admin_user, data={'supervisor_id': self.supervisor2.id})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(RESTRICTED_ADMIN=True)
    def test_change_approver_denied_without_rss_admin_realm(self):
        trip = TripFactory(traveller=self.traveller, supervisor=self.supervisor1)
        trip.status = Trip.STATUS_SUBMITTED
        trip.save()

        non_staff_user = UserFactory(is_staff=False)
        url = reverse('rss_admin:rss-admin-trips-change-approver', kwargs={'pk': trip.pk})
        resp = self.forced_auth_req('patch', url, user=non_staff_user, data={'supervisor_id': self.supervisor2.id})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(RESTRICTED_ADMIN=True)
    def test_change_approver_allowed_with_rss_admin_realm(self):
        trip = TripFactory(traveller=self.traveller, supervisor=self.supervisor1)
        trip.status = Trip.STATUS_SUBMITTED
        trip.save()

        user = UserFactory(is_staff=False)
        group = GroupFactory(name='Rss Admin')
        RealmFactory(user=user, country=self.tenant, group=group, is_active=True)

        url = reverse('rss_admin:rss-admin-trips-change-approver', kwargs={'pk': trip.pk})
        resp = self.forced_auth_req('patch', url, user=user, data={'supervisor_id': self.supervisor2.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        trip.refresh_from_db()
        self.assertEqual(trip.supervisor_id, self.supervisor2.id)
