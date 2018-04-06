from __future__ import absolute_import, division, print_function, unicode_literals

from django.utils import six

from EquiTrack.tests.cases import BaseTenantTestCase
from partners.models import WorkspaceFileType
from partners.tests.factories import InterventionFactory
from snapshot.models import Activity
from snapshot.tests.factories import ActivityFactory
from users.tests.factories import UserFactory


class TestActivity(BaseTenantTestCase):
    def test_str(self):
        user = UserFactory()
        intervention = InterventionFactory()
        activity = ActivityFactory(
            target=intervention,
            action=Activity.CREATE,
            by_user=user
        )
        self.assertEqual(
            six.text_type(activity),
            "{} {} {}".format(user, Activity.CREATE, intervention)
        )

    def test_by_user_display_empty(self):
        user = UserFactory(first_name='', last_name='')
        activity = ActivityFactory(by_user=user)
        self.assertEqual(six.text_type(user), "")
        self.assertEqual(activity.by_user_display(), user.email)

    def test_by_user_display(self):
        user = UserFactory(first_name="First", last_name="Second")
        activity = ActivityFactory(by_user=user)
        self.assertEqual(six.text_type(user), "First Second")
        self.assertEqual(activity.by_user_display(), "First Second")

    def test_delete_target(self):
        workspace = WorkspaceFileType.objects.create(name="Workspace")
        activity = ActivityFactory(target=workspace)
        self.assertEqual(activity.target, workspace)
        workspace.delete()
        self.assertTrue(Activity.objects.filter(pk=activity.pk).exists())
        activity_updated = Activity.objects.get(pk=activity.pk)
        self.assertEqual(
            activity_updated.target_content_type,
            activity.target_content_type
        )
        self.assertEqual(
            activity_updated.target_object_id,
            six.text_type(activity.target_object_id)
        )
        self.assertIsNone(activity_updated.target)
