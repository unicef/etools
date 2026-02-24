from datetime import timedelta

from django.contrib.admin.models import LogEntry
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from rest_framework import status

from etools.applications.action_points.models import ActionPoint
from etools.applications.action_points.tests.factories import ActionPointFactory
from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.rss_admin.admin_logging import log_change
from etools.applications.users.tests.factories import UserFactory


class ActionPointRssAdminTestCase(BaseTenantTestCase):
    """Tests for RSS Admin Action Point API with comments support."""

    @classmethod
    def setUpTestData(cls):
        # Mirror core ActionPoint tests: ensure permissions and notifications are set up
        call_command('update_action_points_permissions', verbosity=0)
        call_command('update_notifications')

        # Create an RSS admin user for authenticating requests
        cls.rss_admin = UserFactory(is_staff=True, realms__data=['RSS'])

    def test_patch_action_point_with_comment(self):
        """Test that RSS admin can PATCH action point with comments."""
        action_point = ActionPointFactory(
            assigned_to=UserFactory(),
            high_priority=True,
            status=ActionPoint.STATUS_COMPLETED,
            comments__count=0,
        )
        url = reverse('rss_admin:rss-admin-action-points-detail', args=[action_point.id])

        # Create an attachment first (simulating file upload)
        attachment = AttachmentFactory(
            file_type=None,
            code='action_points_supporting_document',
        )

        data = {
            'comments': [
                {
                    'comment': 'Test comment with attachment for report',
                    'supporting_document': attachment.id
                }
            ]
        }

        response = self.forced_auth_req(
            'patch',
            url,
            user=self.rss_admin,
            data=data,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        action_point = ActionPoint.objects.get(pk=action_point.pk)

        # Verify the comment was created
        self.assertEqual(action_point.comments.count(), 1)
        comment = action_point.comments.first()
        self.assertEqual(comment.comment, 'Test comment with attachment for report')

        # Verify the attachment is linked to the comment
        self.assertEqual(list(comment.supporting_document.all()), [attachment])

    def test_patch_action_point_with_multiple_comments(self):
        """Test that RSS admin can PATCH action point with multiple comments."""
        action_point = ActionPointFactory(
            assigned_to=UserFactory(),
            high_priority=True,
            status=ActionPoint.STATUS_COMPLETED,
            comments__count=0,
        )
        url = reverse('rss_admin:rss-admin-action-points-detail', args=[action_point.id])

        data = {
            'comments': [
                {'comment': 'First comment'},
                {'comment': 'Second comment'},
            ]
        }

        response = self.forced_auth_req(
            'patch',
            url,
            user=self.rss_admin,
            data=data,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        action_point = ActionPoint.objects.get(pk=action_point.pk)

        # Verify both comments were created
        self.assertEqual(action_point.comments.count(), 2)
        comments = list(action_point.comments.values_list('comment', flat=True))
        self.assertIn('First comment', comments)
        self.assertIn('Second comment', comments)

    def test_patch_action_point_comment_without_attachment(self):
        """Test that RSS admin can add comments without attachments."""
        action_point = ActionPointFactory(
            assigned_to=UserFactory(),
            high_priority=True,
            status=ActionPoint.STATUS_COMPLETED,
            comments__count=0,
        )

        url = reverse('rss_admin:rss-admin-action-points-detail', args=[action_point.id])

        data = {
            'comments': [
                {'comment': 'Comment without attachment'}
            ]
        }

        response = self.forced_auth_req(
            'patch',
            url,
            user=self.rss_admin,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        action_point = ActionPoint.objects.get(pk=action_point.pk)

        # Verify the comment was created without attachment
        self.assertEqual(action_point.comments.count(), 1)
        comment = action_point.comments.first()
        self.assertEqual(comment.comment, 'Comment without attachment')
        self.assertEqual(comment.supporting_document.count(), 0)

    def test_patch_action_point_with_comment_like_curl_request(self):
        """Test PATCH with comments exactly like the curl request from the issue."""
        action_point = ActionPointFactory(
            assigned_to=UserFactory(),
            high_priority=True,
            status=ActionPoint.STATUS_COMPLETED,
            comments__count=0,
        )

        # Create an attachment first (simulating a previously uploaded file)
        attachment = AttachmentFactory(
            file_type=None,
            code='action_points_supporting_document',
        )

        url = reverse('rss_admin:rss-admin-action-points-detail', args=[action_point.id])

        # This mimics the exact curl request: --data-raw '{"comments":[{"comment":"fdgdfgg","supporting_document":5382}]}'
        data = {
            'comments': [
                {
                    'comment': 'fdgdfgg',
                    'supporting_document': attachment.id
                }
            ]
        }

        response = self.forced_auth_req(
            'patch',
            url,
            user=self.rss_admin,
            data=data,
        )

        # Should return 200 OK, not an error
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        action_point = ActionPoint.objects.get(pk=action_point.pk)

        # Verify the comment was created
        self.assertEqual(action_point.comments.count(), 1)
        comment = action_point.comments.first()
        self.assertEqual(comment.comment, 'fdgdfgg')

        # Verify the attachment is linked to the comment
        self.assertEqual(list(comment.supporting_document.all()), [attachment])

    def test_action_point_logs_endpoint(self):
        """Test that action point logs endpoint returns log entries"""
        action_point = ActionPointFactory(assigned_to=UserFactory())
        url = reverse('rss_admin:rss-admin-action-points-logs', kwargs={'pk': action_point.pk})

        # Initially, there should be no logs (or minimal logs)
        resp = self.forced_auth_req('get', url, user=self.rss_admin)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Verify response structure always has pagination keys
        self.assertIn('count', resp.data)
        self.assertIn('next', resp.data)
        self.assertIn('previous', resp.data)
        self.assertIn('results', resp.data)

        initial_count = len(resp.data['results'])

        # Create a log entry directly
        log_change(
            user=self.rss_admin,
            obj=action_point,
            change_message="Test log entry for action point",
        )

        # Now check logs again
        resp = self.forced_auth_req('get', url, user=self.rss_admin)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Verify response structure
        self.assertIn('count', resp.data)
        self.assertIn('next', resp.data)
        self.assertIn('previous', resp.data)
        self.assertIn('results', resp.data)

        logs = resp.data['results']
        self.assertGreater(len(logs), initial_count)
        log_entry = logs[0]  # Most recent log

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

    def test_action_point_logs_filter_search(self):
        """Test that action point logs endpoint supports search filtering"""
        action_point = ActionPointFactory(assigned_to=UserFactory())
        url = reverse('rss_admin:rss-admin-action-points-logs', kwargs={'pk': action_point.pk})

        # Create log entries with different messages
        log_change(
            user=self.rss_admin,
            obj=action_point,
            change_message="Updated status to completed",
        )
        log_change(
            user=self.rss_admin,
            obj=action_point,
            change_message="Changed assigned user",
        )

        # Search for specific text in change_message
        resp = self.forced_auth_req('get', url, user=self.rss_admin, data={'search': 'status'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data['results']
        self.assertGreater(len(results), 0)
        # At least one result should contain 'status'
        self.assertTrue(any('status' in log.get('change_message', '').lower() for log in results))

        # Search for different text
        resp = self.forced_auth_req('get', url, user=self.rss_admin, data={'search': 'assigned'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data['results']
        self.assertGreater(len(results), 0)
        self.assertTrue(any('assigned' in log.get('change_message', '').lower() for log in results))

    def test_action_point_logs_filter_combined(self):
        """Test that action point logs endpoint supports combined filtering"""
        action_point = ActionPointFactory(assigned_to=UserFactory())
        url = reverse('rss_admin:rss-admin-action-points-logs', kwargs={'pk': action_point.pk})

        now = timezone.now()
        old_time = now - timedelta(days=5)

        # Create an old log entry
        old_log = log_change(
            user=self.rss_admin,
            obj=action_point,
            change_message="Important update",
        )
        LogEntry.objects.filter(pk=old_log.pk).update(action_time=old_time)

        # Create a recent log entry
        log_change(
            user=self.rss_admin,
            obj=action_point,
            change_message="Important change",
        )

        # Filter with both search and date range
        date_from = (now - timedelta(days=2)).isoformat()
        resp = self.forced_auth_req('get', url, user=self.rss_admin, data={
            'search': 'Important',
            'action_time_gte': date_from
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data['results']
        # Should have at least one result matching both criteria
        self.assertGreater(len(results), 0)
        for log in results:
            self.assertIn('important', log.get('change_message', '').lower())
