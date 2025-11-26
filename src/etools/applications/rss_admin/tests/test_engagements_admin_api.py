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

    def test_engagement_patch_complex_fields(self):
        """Test that PATCH persists complex engagement fields like those in the curl example"""
        from datetime import date
        audit = AuditFactory(status=Engagement.STATUSES.partner_contacted)
        
        url = reverse('rss_admin:rss-admin-engagements-detail', kwargs={'pk': audit.pk})
        
        # Payload matching the curl example
        payload = {
            'start_date': '2018-10-15',
            'end_date': '2018-12-15',
            'total_value': 1234.00,
        }
        
        resp = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        
        # Verify data persisted in database
        audit.refresh_from_db()
        self.assertEqual(audit.start_date, date(2018, 10, 15))
        self.assertEqual(audit.end_date, date(2018, 12, 15))
        self.assertEqual(float(audit.total_value), 1234.00)

    def test_engagement_patch_audit_specific_fields(self):
        """Test updating audit-specific fields that might have permission restrictions"""
        audit = AuditFactory(status=Engagement.STATUSES.partner_contacted)
        
        url = reverse('rss_admin:rss-admin-engagements-detail', kwargs={'pk': audit.pk})
        
        # Test fields that might be restricted by permissions
        initial_total_value = audit.total_value
        payload = {
            'total_value': 9999.00,
            'exchange_rate': 1.5,
        }
        
        resp = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        
        # Verify changes persisted
        audit.refresh_from_db()
        self.assertEqual(float(audit.total_value), 9999.00)
        self.assertEqual(float(audit.exchange_rate), 1.5)
        self.assertNotEqual(float(audit.total_value), float(initial_total_value))

    def test_engagement_patch_exact_curl_payload(self):
        """Test with the exact payload from the curl request to reproduce the issue"""
        audit = AuditFactory(
            status=Engagement.STATUSES.partner_contacted,
            total_value=999.00
        )
        
        url = reverse('rss_admin:rss-admin-engagements-detail', kwargs={'pk': audit.pk})
        
        # Exact payload from curl (with WRONG field names that frontend is sending)
        payload = {
            'status': 'final',  # WRONG: This is read-only, use change-status endpoint
            'scheduled_year': '2024',  # WRONG: Should be 'year_of_audit'
            'shared_audit_with': 747,  # WRONG: Should be 'shared_ip_with' with agency choices array
            'start_date': '2018-10-15',  # CORRECT
            'end_date': '2018-12-15',  # CORRECT
            'total_value_usd': '1234',  # WRONG: Should be 'total_value'
            'total_value_local': '1235',  # WRONG: Not a field
        }
        
        resp = self.forced_auth_req('patch', url, user=self.user, data=payload)
        # Should succeed even with invalid fields (they're just ignored)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        
        # Verify that ONLY valid fields persisted
        audit.refresh_from_db()
        self.assertEqual(str(audit.start_date), '2018-10-15')
        self.assertEqual(str(audit.end_date), '2018-12-15')
        # Invalid fields were ignored, so total_value remains unchanged
        self.assertEqual(float(audit.total_value), 999.00)  # NOT changed to 1234
        
    def test_engagement_patch_with_correct_field_names(self):
        """Test with CORRECT field names to show the difference"""
        audit = AuditFactory(
            status=Engagement.STATUSES.partner_contacted,
            total_value=999.00
        )
        
        url = reverse('rss_admin:rss-admin-engagements-detail', kwargs={'pk': audit.pk})
        
        # CORRECT payload with proper field names
        payload = {
            # 'status' should be updated via change-status endpoint, not here
            'year_of_audit': 2024,  # CORRECT field name
            'shared_ip_with': ['UNDP'],  # CORRECT field name and format
            'start_date': '2018-10-15',
            'end_date': '2018-12-15',
            'total_value': 1234.00,  # CORRECT field name
        }
        
        resp = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        
        # Verify ALL fields persisted
        audit.refresh_from_db()
        self.assertEqual(audit.year_of_audit, 2024)
        self.assertEqual(audit.shared_ip_with, ['UNDP'])
        self.assertEqual(str(audit.start_date), '2018-10-15')
        self.assertEqual(str(audit.end_date), '2018-12-15')
        self.assertEqual(float(audit.total_value), 1234.00)  # NOW it changed!

    def test_engagement_patch_shared_ip_with(self):
        """Test updating shared_ip_with field with agency choices"""
        audit = AuditFactory(status=Engagement.STATUSES.partner_contacted)
        
        url = reverse('rss_admin:rss-admin-engagements-detail', kwargs={'pk': audit.pk})
        
        payload = {
            'shared_ip_with': ['UNDP', 'FAO'],  # Agency choice strings, not partner IDs
        }
        
        resp = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        
        # Verify the data was set
        audit.refresh_from_db()
        self.assertEqual(audit.shared_ip_with, ['UNDP', 'FAO'])

    def test_engagement_patch_persistence_across_requests(self):
        """Test that PATCH changes persist when retrieving the engagement again"""
        from datetime import date
        audit = AuditFactory(
            status=Engagement.STATUSES.partner_contacted,
            total_value=100.00,
            exchange_rate=1.0
        )
        
        url = reverse('rss_admin:rss-admin-engagements-detail', kwargs={'pk': audit.pk})
        
        # Step 1: PATCH with new values
        payload = {
            'start_date': '2018-10-15',
            'end_date': '2018-12-15',
            'total_value': 5678.00,
            'exchange_rate': 1.25,
            'shared_ip_with': ['UNDP'],
        }
        
        patch_resp = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK, patch_resp.data)
        
        # Step 2: Check the PATCH response has the updated values
        self.assertEqual(patch_resp.data['start_date'], '2018-10-15')
        self.assertEqual(patch_resp.data['end_date'], '2018-12-15')
        self.assertEqual(float(patch_resp.data['total_value']), 5678.00)
        self.assertEqual(float(patch_resp.data['exchange_rate']), 1.25)
        self.assertEqual(patch_resp.data['shared_ip_with'], ['UNDP'])
        
        # Step 3: GET the engagement again to verify persistence
        get_resp = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(get_resp.status_code, status.HTTP_200_OK)
        
        # Step 4: Verify all fields persisted in the GET response
        self.assertEqual(get_resp.data['start_date'], '2018-10-15')
        self.assertEqual(get_resp.data['end_date'], '2018-12-15')
        self.assertEqual(float(get_resp.data['total_value']), 5678.00)
        self.assertEqual(float(get_resp.data['exchange_rate']), 1.25)
        self.assertEqual(get_resp.data['shared_ip_with'], ['UNDP'])
        
        # Step 5: Verify in database
        audit.refresh_from_db()
        self.assertEqual(audit.start_date, date(2018, 10, 15))
        self.assertEqual(audit.end_date, date(2018, 12, 15))
        self.assertEqual(float(audit.total_value), 5678.00)
        self.assertEqual(float(audit.exchange_rate), 1.25)
        self.assertEqual(audit.shared_ip_with, ['UNDP'])

