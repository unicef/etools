from django.urls import reverse
from rest_framework import status

from etools.applications.action_points.models import ActionPoint, ActionPointComment
from etools.applications.action_points.tests.factories import ActionPointFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.users.tests.factories import UserFactory
from unicef_attachments.models import Attachment


class ActionPointRssAdminTestCase(BaseTenantTestCase):
    """Tests for RSS Admin Action Point API with comments support."""

    @classmethod
    def setUpTestData(cls):
        cls.rss_admin = UserFactory(is_staff=True, realms__data=['RSS'])

    def test_patch_action_point_with_comment(self):
        """Test that RSS admin can PATCH action point with comments."""
        action_point = ActionPointFactory(
            assigned_to=UserFactory(),
            high_priority=True,
            status=ActionPoint.STATUS_COMPLETED
        )
        
        self.client.force_authenticate(self.rss_admin)
        url = reverse('rss_admin:action-points-detail', args=[action_point.id])
        
        # Create an attachment first (simulating file upload)
        attachment = Attachment.objects.create(
            file_type='some_type',
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
        
        response = self.client.patch(url, data=data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        action_point.refresh_from_db()
        
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
            status=ActionPoint.STATUS_COMPLETED
        )
        
        self.client.force_authenticate(self.rss_admin)
        url = reverse('rss_admin:action-points-detail', args=[action_point.id])
        
        data = {
            'comments': [
                {'comment': 'First comment'},
                {'comment': 'Second comment'},
            ]
        }
        
        response = self.client.patch(url, data=data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        action_point.refresh_from_db()
        
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
            status=ActionPoint.STATUS_COMPLETED
        )
        
        self.client.force_authenticate(self.rss_admin)
        url = reverse('rss_admin:action-points-detail', args=[action_point.id])
        
        data = {
            'comments': [
                {'comment': 'Comment without attachment'}
            ]
        }
        
        response = self.client.patch(url, data=data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        action_point.refresh_from_db()
        
        # Verify the comment was created without attachment
        self.assertEqual(action_point.comments.count(), 1)
        comment = action_point.comments.first()
        self.assertEqual(comment.comment, 'Comment without attachment')
        self.assertEqual(comment.supporting_document.count(), 0)

