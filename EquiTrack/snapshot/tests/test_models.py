from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from EquiTrack.factories import (
    ActivityFactory,
    InterventionFactory,
    UserFactory,
)
from EquiTrack.tests.cases import EToolsTenantTestCase
from snapshot.models import Activity
from partners.models import WorkspaceFileType


class TestActivity(EToolsTenantTestCase):
    def test_str(self):
        user = UserFactory()
        intervention = InterventionFactory()
        activity = ActivityFactory(
            target=intervention,
            action=Activity.CREATE,
            by_user=user
        )
        self.assertEqual(
            str(activity),
            "{} {} {}".format(user, Activity.CREATE, intervention)
        )

    def test_by_user_display_empty(self):
        user = UserFactory()
        activity = ActivityFactory(by_user=user)
        self.assertEqual(str(user), "")
        self.assertEqual(activity.by_user_display(), user.email)

    def test_by_user_display(self):
        user = UserFactory(first_name="First")
        activity = ActivityFactory(by_user=user)
        self.assertEqual(str(user), "First")
        self.assertEqual(activity.by_user_display(), "First")

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
            str(activity.target_object_id)
        )
        self.assertIsNone(activity_updated.target)
