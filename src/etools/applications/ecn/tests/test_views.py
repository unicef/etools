from unittest.mock import patch

from django.urls import reverse

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.ecn.tests.utils import get_example_ecn
from etools.applications.partners.permissions import PARTNERSHIP_MANAGER_GROUP, UNICEF_USER
from etools.applications.partners.tests.factories import AgreementFactory
from etools.applications.users.tests.factories import UserFactory


class SyncViewTestCase(BaseTenantTestCase):
    @patch('etools.applications.ecn.api.ECNAPI.get_intervention')
    def test_sync(self, request_intervention_mock):
        request_intervention_mock.return_value = get_example_ecn()

        agreement = AgreementFactory()
        response = self.forced_auth_req(
            'post',
            reverse('ecn_v1:intervention-import-ecn'),
            user=UserFactory(groups__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]),
            data={
                'agreement': agreement.pk,
                'number': 'test',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_permissions(self):
        agreement = AgreementFactory()
        response = self.forced_auth_req(
            'post',
            reverse('ecn_v1:intervention-import-ecn'),
            user=UserFactory(groups__data=[UNICEF_USER]),
            data={
                'agreement': agreement.pk,
                'number': 'test',
            }
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
