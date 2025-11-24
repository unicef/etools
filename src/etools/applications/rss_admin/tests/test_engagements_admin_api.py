from django.test import override_settings
from django.urls import reverse

from rest_framework import status

from etools.applications.audit.models import Engagement
from etools.applications.audit.tests.factories import AuditFactory, SpotCheckFactory, StaffSpotCheckFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.users.tests.factories import UserFactory


@override_settings(RESTRICTED_ADMIN=False)
class TestRssAdminEngagementsApi(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory(is_staff=True)

    def test_engagement_list(self):
        """Test that engagement list endpoint works"""
        AuditFactory()
        url = reverse('rss_admin:rss-admin-engagements-list')
        resp = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('results', resp.data)

    def test_engagement_retrieve(self):
        """Test that engagement retrieve endpoint works"""
        audit = AuditFactory()
        url = reverse('rss_admin:rss-admin-engagements-detail', kwargs={'pk': audit.pk})
        resp = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['id'], audit.pk)

    def test_engagement_patch_audit(self):
        """Test that PATCH method works for audit engagement"""
        audit = AuditFactory(status=Engagement.STATUSES.partner_contacted)
        url = reverse('rss_admin:rss-admin-engagements-detail', kwargs={'pk': audit.pk})
        
        # Update some fields
        payload = {
            'total_value': 5000.00,
        }
        resp = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        
        # Verify the update
        audit.refresh_from_db()
        self.assertEqual(float(audit.total_value), 5000.00)

    def test_engagement_patch_spot_check(self):
        """Test that PATCH method works for spot check engagement"""
        spot_check = SpotCheckFactory(status=Engagement.STATUSES.partner_contacted)
        url = reverse('rss_admin:rss-admin-engagements-detail', kwargs={'pk': spot_check.pk})
        
        # Update some fields
        payload = {
            'total_value': 3000.00,
        }
        resp = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        
        # Verify the update
        spot_check.refresh_from_db()
        self.assertEqual(float(spot_check.total_value), 3000.00)

    def test_engagement_patch_staff_spot_check(self):
        """Test that PATCH method works for staff spot check engagement"""
        staff_sc = StaffSpotCheckFactory(status=Engagement.STATUSES.partner_contacted)
        url = reverse('rss_admin:rss-admin-engagements-detail', kwargs={'pk': staff_sc.pk})
        
        # Update some fields
        payload = {
            'total_value': 2000.00,
        }
        resp = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        
        # Verify the update
        staff_sc.refresh_from_db()
        self.assertEqual(float(staff_sc.total_value), 2000.00)

    def test_engagement_patch_non_staff_forbidden(self):
        """Test that non-staff users cannot PATCH engagements"""
        non_staff_user = UserFactory(is_staff=False)
        audit = AuditFactory()
        url = reverse('rss_admin:rss-admin-engagements-detail', kwargs={'pk': audit.pk})
        
        payload = {
            'total_value': 5000.00,
        }
        resp = self.forced_auth_req('patch', url, user=non_staff_user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_engagement_patch_multiple_fields(self):
        """Test that PATCH method can update multiple fields at once"""
        audit = AuditFactory(status=Engagement.STATUSES.partner_contacted)
        url = reverse('rss_admin:rss-admin-engagements-detail', kwargs={'pk': audit.pk})
        
        # Update multiple fields
        payload = {
            'total_value': 7500.00,
            'exchange_rate': 1.25,
        }
        resp = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        
        # Verify the updates
        audit.refresh_from_db()
        self.assertEqual(float(audit.total_value), 7500.00)
        self.assertEqual(float(audit.exchange_rate), 1.25)

    def test_engagement_patch_returns_full_serialized_data(self):
        """Test that PATCH response includes full engagement data"""
        audit = AuditFactory(status=Engagement.STATUSES.partner_contacted)
        url = reverse('rss_admin:rss-admin-engagements-detail', kwargs={'pk': audit.pk})
        
        payload = {
            'total_value': 4500.00,
        }
        resp = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        
        # Check that response includes key fields
        self.assertIn('id', resp.data)
        self.assertIn('engagement_type', resp.data)
        self.assertIn('partner', resp.data)
        self.assertEqual(resp.data['id'], audit.pk)

