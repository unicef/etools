__author__ = 'jcranwellward'

from django.test import TestCase

from EquiTrack.factories import UserFactory


class TestUserModel(TestCase):

    def test_create_user(self):
        user = UserFactory(
            profile__job_title='Chief Tea Maker'
        )
        self.assertTrue(
            'Chief Tea Maker',
            user.get_profile().job_title
        )