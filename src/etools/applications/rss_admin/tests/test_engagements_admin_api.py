from unittest import mock

from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.urls import reverse

from rest_framework import status

from etools.applications.attachments.tests.factories import AttachmentFactory, AttachmentFileTypeFactory
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
        """Test with the exact payload from the curl request to show field name issues"""
        audit = AuditFactory(
            status=Engagement.STATUSES.partner_contacted,
            total_value=999.00
        )

        url = reverse('rss_admin:rss-admin-engagements-detail', kwargs={'pk': audit.pk})

        # Exact payload from curl (with WRONG field names that frontend is sending)
        payload = {
            'status': 'final',  # WRONG: Invalid transition (can't go directly from partner_contacted to final)
            'scheduled_year': '2024',  # WRONG: Should be 'year_of_audit'
            'shared_audit_with': 747,  # WRONG: Should be 'shared_ip_with' with agency choices array
            'start_date': '2018-10-15',  # CORRECT
            'end_date': '2018-12-15',  # CORRECT
            'total_value_usd': '1234',  # WRONG: Should be 'total_value'
            'total_value_local': '1235',  # WRONG: Not a field
        }

        resp = self.forced_auth_req('patch', url, user=self.user, data=payload)
        # Invalid status transition will fail
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Invalid status transition', str(resp.data))

        # Try again without invalid status transition
        payload_without_status = {
            'scheduled_year': '2024',  # WRONG field name - will be ignored
            'start_date': '2018-10-15',  # CORRECT
            'end_date': '2018-12-15',  # CORRECT
            'total_value_usd': '1234',  # WRONG field name - will be ignored
        }

        resp2 = self.forced_auth_req('patch', url, user=self.user, data=payload_without_status)
        self.assertEqual(resp2.status_code, status.HTTP_200_OK, resp2.data)

        # Verify that ONLY valid fields persisted
        audit.refresh_from_db()
        self.assertEqual(str(audit.start_date), '2018-10-15')
        self.assertEqual(str(audit.end_date), '2018-12-15')
        # Invalid field names were ignored, so total_value remains unchanged
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

    def test_engagement_patch_status_triggers_fsm_submit(self):
        """Test that changing status via PATCH triggers FSM submit transition"""
        from datetime import date
        audit = AuditFactory(
            status=Engagement.STATUSES.partner_contacted,
            date_of_field_visit=date(2024, 1, 15),
            date_of_draft_report_to_ip=date(2024, 1, 20),
            date_of_comments_by_ip=date(2024, 1, 25),
            date_of_draft_report_to_unicef=date(2024, 1, 30),
            date_of_comments_by_unicef=date(2024, 2, 5),
            audited_expenditure=10000,
            audit_opinion='qualified',
            currency_of_report='USD'
        )

        # Add required report attachment with proper file_type
        file_type = AttachmentFileTypeFactory(name='report', code='audit_report')
        attachment = AttachmentFactory(code='audit_report', file='test.pdf', file_type=file_type)
        audit.report_attachments.add(attachment)

        url = reverse('rss_admin:rss-admin-engagements-detail', kwargs={'pk': audit.pk})

        # Change status from partner_contacted to report_submitted
        payload = {
            'status': Engagement.STATUSES.report_submitted
        }

        resp = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)

        # Verify status changed and FSM side effects occurred
        audit.refresh_from_db()
        self.assertEqual(audit.status, Engagement.STATUSES.report_submitted)
        self.assertIsNotNone(audit.date_of_report_submit)  # FSM sets this

    def test_engagement_patch_status_triggers_fsm_finalize(self):
        """Test that changing status via PATCH triggers FSM finalize transition"""
        audit = AuditFactory(status=Engagement.STATUSES.report_submitted)
        url = reverse('rss_admin:rss-admin-engagements-detail', kwargs={'pk': audit.pk})

        # Change status to final
        payload = {
            'status': Engagement.STATUSES.final
        }

        with mock.patch.object(audit.__class__, 'generate_final_report'):
            resp = self.forced_auth_req('patch', url, user=self.user, data=payload)
            self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)

        # Verify status changed and FSM side effects occurred
        audit.refresh_from_db()
        self.assertEqual(audit.status, Engagement.STATUSES.final)
        self.assertIsNotNone(audit.date_of_final_report)  # FSM sets this

    def test_engagement_patch_status_send_back_requires_comment(self):
        """Test that send_back transition via PATCH requires a comment"""
        audit = AuditFactory(status=Engagement.STATUSES.report_submitted)
        url = reverse('rss_admin:rss-admin-engagements-detail', kwargs={'pk': audit.pk})

        # Try to send back without comment - should fail
        payload = {
            'status': Engagement.STATUSES.partner_contacted
        }

        resp = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('send_back_comment', str(resp.data))

        # Now with comment - should succeed
        payload['send_back_comment'] = 'Please revise the report'
        resp = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        audit.refresh_from_db()
        self.assertEqual(audit.status, Engagement.STATUSES.partner_contacted)
        self.assertEqual(audit.send_back_comment, 'Please revise the report')
        self.assertIsNone(audit.date_of_report_submit)  # FSM clears this

    def test_engagement_patch_status_cancel_requires_comment(self):
        """Test that cancel transition via PATCH requires a comment"""
        audit = AuditFactory(status=Engagement.STATUSES.partner_contacted)
        url = reverse('rss_admin:rss-admin-engagements-detail', kwargs={'pk': audit.pk})

        # Try to cancel without comment - should fail
        payload = {
            'status': Engagement.STATUSES.cancelled
        }

        resp = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cancel_comment', str(resp.data))

        # Now with comment - should succeed
        payload['cancel_comment'] = 'Engagement no longer needed'
        resp = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        audit.refresh_from_db()
        self.assertEqual(audit.status, Engagement.STATUSES.cancelled)
        self.assertEqual(audit.cancel_comment, 'Engagement no longer needed')
        self.assertIsNotNone(audit.date_of_cancel)  # FSM sets this

    def test_engagement_patch_invalid_status_transition(self):
        """Test that invalid status transitions are rejected"""
        audit = AuditFactory(status=Engagement.STATUSES.partner_contacted)
        url = reverse('rss_admin:rss-admin-engagements-detail', kwargs={'pk': audit.pk})

        # Try to jump directly to final (invalid transition)
        payload = {
            'status': Engagement.STATUSES.final
        }

        resp = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Invalid status transition', str(resp.data))

        # Verify status didn't change
        audit.refresh_from_db()
        self.assertEqual(audit.status, Engagement.STATUSES.partner_contacted)

    def test_engagement_patch_status_with_other_fields(self):
        """Test that status change can be combined with other field updates"""
        from datetime import date
        audit = AuditFactory(
            status=Engagement.STATUSES.partner_contacted,
            total_value=1000,
            date_of_field_visit=date(2024, 1, 15),
            date_of_draft_report_to_ip=date(2024, 1, 20),
            date_of_comments_by_ip=date(2024, 1, 25),
            date_of_draft_report_to_unicef=date(2024, 1, 30),
            date_of_comments_by_unicef=date(2024, 2, 5),
            audited_expenditure=10000,
            audit_opinion='qualified',
            currency_of_report='USD'
        )

        # Add required report attachment
        file_type = AttachmentFileTypeFactory(name='report', code='audit_report')
        attachment = AttachmentFactory(code='audit_report', file='test.pdf', file_type=file_type)
        audit.report_attachments.add(attachment)

        url = reverse('rss_admin:rss-admin-engagements-detail', kwargs={'pk': audit.pk})

        # Change status and other fields together
        payload = {
            'status': Engagement.STATUSES.report_submitted,
            'total_value': 5000.00
        }

        resp = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Verify both changes took effect
        audit.refresh_from_db()
        self.assertEqual(audit.status, Engagement.STATUSES.report_submitted)
        self.assertEqual(float(audit.total_value), 5000.00)
        self.assertIsNotNone(audit.date_of_report_submit)  # FSM side effect

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

    def test_engagement_patch_error_format_consistency(self):
        """Test that all errors follow the format: {'field': ['error message']}"""
        audit = AuditFactory(status=Engagement.STATUSES.partner_contacted)
        url = reverse('rss_admin:rss-admin-engagements-detail', kwargs={'pk': audit.pk})

        # Test 1: Invalid status transition
        payload = {'status': Engagement.STATUSES.final}
        resp = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', resp.data)
        self.assertIsInstance(resp.data['status'], list, "Error should be a list")
        self.assertTrue(len(resp.data['status']) > 0)
        self.assertIn('Invalid status transition', resp.data['status'][0])

        # Test 2: Missing send_back_comment
        audit.status = Engagement.STATUSES.report_submitted
        audit.save()
        payload = {'status': Engagement.STATUSES.partner_contacted}
        resp = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('send_back_comment', resp.data)
        self.assertIsInstance(resp.data['send_back_comment'], list, "Error should be a list")
        self.assertTrue(len(resp.data['send_back_comment']) > 0)
        self.assertIn('required', resp.data['send_back_comment'][0])

        # Test 3: Missing cancel_comment
        audit.status = Engagement.STATUSES.partner_contacted
        audit.save()
        payload = {'status': Engagement.STATUSES.cancelled}
        resp = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cancel_comment', resp.data)
        self.assertIsInstance(resp.data['cancel_comment'], list, "Error should be a list")
        self.assertTrue(len(resp.data['cancel_comment']) > 0)
        self.assertIn('required', resp.data['cancel_comment'][0])

    def test_engagement_attachments_include_filename(self):
        """Test that engagement and report attachment endpoints include filename field"""
        audit = AuditFactory(status=Engagement.STATUSES.partner_contacted)

        # Create engagement attachment
        engagement_file_type = AttachmentFileTypeFactory(code='audit_engagement')
        engagement_attachment = AttachmentFactory(
            code='audit_engagement',
            content_object=audit,
            file_type=engagement_file_type,
            file='test_engagement_document.pdf'
        )

        # Create report attachment
        report_file_type = AttachmentFileTypeFactory(code='audit_report')
        report_attachment = AttachmentFactory(
            code='audit_report',
            content_object=audit,
            file_type=report_file_type,
            file='test_audit_report.pdf'
        )

        # Test engagement-attachments endpoint
        engagement_url = reverse('rss_admin:rss-admin-engagement-attachments-list',
                                 kwargs={'engagement_pk': audit.pk})
        resp = self.forced_auth_req('get', engagement_url, user=self.user)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data), 1)
        # Find our attachment in the response and verify it has filename
        engagement_ids = [item['id'] for item in resp.data]
        self.assertIn(engagement_attachment.id, engagement_ids)
        our_attachment = next(item for item in resp.data if item['id'] == engagement_attachment.id)
        self.assertIn('filename', our_attachment)
        self.assertIsNotNone(our_attachment['filename'])

        # Test report-attachments endpoint
        report_url = reverse('rss_admin:rss-admin-report-attachments-list',
                             kwargs={'engagement_pk': audit.pk})
        resp = self.forced_auth_req('get', report_url, user=self.user)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data), 1)
        # Find our attachment in the response and verify it has filename
        report_ids = [item['id'] for item in resp.data]
        self.assertIn(report_attachment.id, report_ids)
        our_report = next(item for item in resp.data if item['id'] == report_attachment.id)
        self.assertIn('filename', our_report)
        self.assertIsNotNone(our_report['filename'])

    def test_engagement_logs_endpoint(self):
        """Test that engagement logs endpoint returns log entries"""
        audit = AuditFactory()
        url = reverse('rss_admin:rss-admin-engagements-logs', kwargs={'pk': audit.pk})

        # Initially, there should be no logs
        resp = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        if 'results' in resp.data:
            initial_count = len(resp.data['results'])
        else:
            initial_count = len(resp.data)

        # Make a change to create a log entry
        payload = {'total_value': 1000.00}
        patch_url = reverse('rss_admin:rss-admin-engagements-detail', kwargs={'pk': audit.pk})
        self.forced_auth_req('patch', patch_url, user=self.user, data=payload)

        # Now check logs again
        resp = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Verify log structure
        if 'results' in resp.data:
            logs = resp.data['results']
            self.assertGreater(len(logs), initial_count)
            log_entry = logs[0]  # Most recent log
        else:
            logs = resp.data
            self.assertGreater(len(logs), initial_count)
            log_entry = logs[0]

        # Verify log entry has required fields
        self.assertIn('id', log_entry)
        self.assertIn('action_time', log_entry)
        self.assertIn('user', log_entry)
        self.assertIn('action_flag', log_entry)
        self.assertIn('action_flag_display', log_entry)
        self.assertIn('change_message', log_entry)
        self.assertIn('content_type_display', log_entry)
        self.assertIn('object_id', log_entry)
        self.assertIn('object_repr', log_entry)

        # Verify user information
        if log_entry['user']:
            self.assertIn('id', log_entry['user'])
            self.assertIn('username', log_entry['user'])

        # Verify action flag display
        self.assertIn(log_entry['action_flag_display'], ['Addition', 'Change', 'Deletion'])

    def test_engagement_logs_pagination(self):
        """Test that engagement logs endpoint supports pagination"""
        audit = AuditFactory()
        url = reverse('rss_admin:rss-admin-engagements-logs', kwargs={'pk': audit.pk})

        # Make multiple changes to create multiple log entries
        for i in range(3):
            payload = {'total_value': float(1000 + i * 100)}
            patch_url = reverse('rss_admin:rss-admin-engagements-detail', kwargs={'pk': audit.pk})
            self.forced_auth_req('patch', patch_url, user=self.user, data=payload)

        # Request with pagination
        resp = self.forced_auth_req('get', url, user=self.user, data={'page_size': 2})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Should have pagination structure
        if 'results' in resp.data:
            self.assertIn('count', resp.data)
            self.assertIn('next', resp.data)
            self.assertIn('previous', resp.data)
            self.assertIn('results', resp.data)
            self.assertLessEqual(len(resp.data['results']), 2)

    def test_engagement_logs_creates_entry_on_update(self):
        """Test that updating an engagement creates a log entry"""
        audit = AuditFactory(total_value=500.00)
        content_type = ContentType.objects.get_for_model(audit.__class__)

        # Count initial log entries
        initial_logs = LogEntry.objects.filter(
            content_type=content_type,
            object_id=str(audit.pk)
        ).count()

        # Update the engagement
        url = reverse('rss_admin:rss-admin-engagements-detail', kwargs={'pk': audit.pk})
        payload = {'total_value': 1500.00}
        resp = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Verify a log entry was created
        new_logs = LogEntry.objects.filter(
            content_type=content_type,
            object_id=str(audit.pk)
        ).count()
        self.assertGreater(new_logs, initial_logs)

        # Verify the log entry has correct information
        log_entry = LogEntry.objects.filter(
            content_type=content_type,
            object_id=str(audit.pk)
        ).order_by('-action_time').first()

        self.assertIsNotNone(log_entry)
        self.assertEqual(log_entry.user, self.user)
        self.assertEqual(log_entry.action_flag, CHANGE)
        self.assertIn('total_value', log_entry.change_message.lower())
