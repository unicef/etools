__author__ = 'jcranwellward'

from EquiTrack.tests.mixins import FastTenantTestCase as TenantTestCase

from EquiTrack.factories import UserFactory


class TestUserModel(TenantTestCase):

    def test_create_user(self):
        user = UserFactory(
            profile__job_title='Chief Tea Maker'
        )
        self.assertTrue(
            'Chief Tea Maker',
            user.profile.job_title
        )