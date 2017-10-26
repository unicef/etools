from __future__ import unicode_literals

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import FastTenantTestCase as TenantTestCase


class TestUserModel(TenantTestCase):

    def test_create_user(self):
        user = UserFactory(
            profile__job_title='Chief Tea Maker'
        )
        self.assertTrue(
            'Chief Tea Maker',
            user.profile.job_title
        )

    def test_conversion_to_string(self):
        '''Exercise converting instances to string.'''
        user = UserFactory(first_name='Pel\xe9', last_name='Arantes do Nascimento')
        self.assertEqual(unicode(user), 'Pel\xe9 Arantes do Nascimento')
