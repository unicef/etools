from EquiTrack.factories import (
    ActivityFactory,
    InterventionFactory,
    UserFactory,
)
from EquiTrack.tests.mixins import FastTenantTestCase as TenantTestCase
from snapshot.models import Activity


class TestActivity(TenantTestCase):
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
