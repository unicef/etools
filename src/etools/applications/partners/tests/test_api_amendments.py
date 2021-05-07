from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.users.tests.factories import UserFactory
from etools.applications.partners.models import InterventionAmendment
from etools.applications.partners.tests.factories import InterventionFactory


class TestInterventionAmendments(BaseTenantTestCase):
    # @classmethod
    # def setUpTestData(cls):
    #     cls.user = UserFactory(is_staff=True)
    #     cls.url = reverse("partners_api:dropdown-static-list")

    def test_start_amendment(self):
        intervention = InterventionFactory()
        response = self.forced_auth_req(
            'post',
            reverse('partners_api:intervention-amendments-add', args=[intervention.pk]),
            UserFactory(is_staff=True, groups__data=['UNICEF User', 'Partnership Manager']),
            data={
                'types': [InterventionAmendment.TYPE_CHANGE],
                'signed_amendment': SimpleUploadedFile('hello_world.txt', 'hello world!'.encode('utf-8')),
                'signed_date': (timezone.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                'kind': InterventionAmendment.KIND_NORMAL,
            },
            request_format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        print(response.data)

        response = self.forced_auth_req(
            'post',
            reverse('partners_api:intervention-amendments-add', args=[intervention.pk]),
            UserFactory(is_staff=True, groups__data=['UNICEF User', 'Partnership Manager']),
            data={
                'types': [InterventionAmendment.TYPE_CHANGE],
                'signed_amendment': SimpleUploadedFile('hello_world.txt', 'hello world!'.encode('utf-8')),
                'signed_date': (timezone.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                'kind': InterventionAmendment.KIND_CONTINGENCY,
            },
            request_format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        print(response.data)

        response = self.forced_auth_req(
            'post',
            reverse('partners_api:intervention-amendments-add', args=[intervention.pk]),
            UserFactory(is_staff=True, groups__data=['UNICEF User', 'Partnership Manager']),
            data={
                'types': [InterventionAmendment.TYPE_CHANGE],
                'signed_amendment': SimpleUploadedFile('hello_world.txt', 'hello world!'.encode('utf-8')),
                'signed_date': (timezone.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                'kind': InterventionAmendment.KIND_CONTINGENCY,
            },
            request_format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        print(response.data)
