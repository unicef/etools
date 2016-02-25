__author__ = 'unicef-leb-inn'

from rest_framework import status

from EquiTrack.factories import PartnershipFactory, UserFactory
from EquiTrack.tests.mixins import APITenantTestCase

from partners.models import PCA


class TestPartnershipViews(APITenantTestCase):

    def setUp(self):
        self.unicef_staff = UserFactory(is_staff=True)
        self.intervention = PartnershipFactory()

        # self.client.login(
        #     username=self.unicef_staff.username,
        #     password='test'
        # )

    def test_view_trips_list(self):

        response = self.forced_auth_req('get', '/api/interventions/', user=self.unicef_staff)

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        # the length of this list should be 1
        self.assertEquals(len(response.data), 1)


