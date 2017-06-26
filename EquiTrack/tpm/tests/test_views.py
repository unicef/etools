from django.core.management import call_command

from rest_framework import status

from EquiTrack.tests.mixins import APITenantTestCase
from .base import TPMTestCaseMixin
from .factories import TPMVisitFactory


class TestTPMVisitViewSet(TPMTestCaseMixin, APITenantTestCase):
    def setUp(self):
        super(TestTPMVisitViewSet, self).setUp()
        call_command('update_tpm_permissions')

    def _test_list_view(self, user, expected_visits):
        response = self.forced_auth_req(
            'get',
            '/api/tpm/visits/',
            user=user
        )

        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertListEqual(
            sorted(map(lambda x: x['id'], response.data['results'])),
            sorted(map(lambda x: x.id, expected_visits))
        )

    def test_list_view(self):
        additional_tpm_visit = TPMVisitFactory()

        self._test_list_view(self.pme_user, [self.tpm_visit, additional_tpm_visit, ])
        self._test_list_view(self.unicef_user, [self.tpm_visit, additional_tpm_visit, ])
        self._test_list_view(self.unicef_focal_point, [self.tpm_visit, additional_tpm_visit, ])

        self._test_list_view(self.tpm_user, [self.tpm_visit, ])

        self._test_list_view(self.usual_user, [])
