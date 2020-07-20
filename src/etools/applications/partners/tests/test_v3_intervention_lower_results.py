from django.urls import reverse
from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.tests.factories import InterventionFactory, InterventionResultLinkFactory
from etools.applications.reports.models import ResultType, LowerResult
from etools.applications.reports.tests.factories import ResultFactory, LowerResultFactory
from etools.applications.users.tests.factories import UserFactory


class TestInterventionLowerResultsView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.intervention = InterventionFactory()
        cls.cp_output = ResultFactory(result_type__name=ResultType.OUTPUT)
        cls.result_link = InterventionResultLinkFactory(intervention=cls.intervention, cp_output=cls.cp_output)

    def test_list(self):
        LowerResultFactory(intervention=self.intervention)
        LowerResultFactory(result_link=self.result_link)

        response = self.forced_auth_req(
            'get', reverse('partners:intervention-pd-outputs', args=[self.intervention.pk]), self.user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual([r['cp_output'] for r in response.data], [None, self.cp_output.id])

    def test_create_unassociated(self):
        response = self.forced_auth_req(
            'post', reverse('partners:intervention-pd-outputs', args=[self.intervention.pk]), self.user,
            data={'name': 'test', 'code': 'test'}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        pd_result = LowerResult.objects.get(id=response.data['id'])
        self.assertEqual(pd_result.intervention, self.intervention)
        self.assertEqual(pd_result.result_link, None)

    def test_create_associated(self):
        response = self.forced_auth_req(
            'post', reverse('partners:intervention-pd-outputs', args=[self.intervention.pk]), self.user,
            data={'name': 'test', 'code': 'test', 'cp_output': self.cp_output.id}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        pd_result = LowerResult.objects.get(id=response.data['id'])
        self.assertEqual(pd_result.intervention, self.intervention)
        self.assertEqual(pd_result.result_link.cp_output, self.cp_output)
