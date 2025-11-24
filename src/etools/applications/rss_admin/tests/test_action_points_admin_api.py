from django.core.management import call_command
from django.urls import reverse

from rest_framework import status

from etools.applications.action_points.models import ActionPoint
from etools.applications.action_points.tests.factories import ActionPointFactory
from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
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
