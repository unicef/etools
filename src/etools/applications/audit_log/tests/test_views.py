from django.contrib.contenttypes.models import ContentType

from rest_framework import status
from rest_framework.reverse import reverse

from etools.applications.audit_log.models import AuditLogEntry
from etools.applications.audit_log.tests.factories import AuditLogEntryFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import PartnerOrganization
from etools.applications.users.tests.factories import UserFactory


class TestAuditLogEntryViewSet(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.ct = ContentType.objects.get_for_model(PartnerOrganization)
        cls.entry1 = AuditLogEntryFactory(
            content_type=cls.ct,
            object_id='1',
            action=AuditLogEntry.ACTION_CREATE,
            user=cls.user,
            new_values={'name': 'Test'},
        )
        cls.entry2 = AuditLogEntryFactory(
            content_type=cls.ct,
            object_id='1',
            action=AuditLogEntry.ACTION_UPDATE,
            user=cls.user,
            changed_fields=['name'],
            old_values={'name': 'Test'},
            new_values={'name': 'Updated'},
        )
        cls.entry3 = AuditLogEntryFactory(
            content_type=cls.ct,
            object_id='2',
            action=AuditLogEntry.ACTION_DELETE,
            user=cls.user,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_list_returns_all(self):
        url = reverse('audit_log:audit-log-entries-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)

    def test_filter_by_object_id(self):
        url = reverse('audit_log:audit-log-entries-list')
        response = self.client.get(url, {'object_id': '1'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

    def test_filter_by_action(self):
        url = reverse('audit_log:audit-log-entries-list')
        response = self.client.get(url, {'action': 'DELETE'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_filter_by_content_type(self):
        url = reverse('audit_log:audit-log-entries-list')
        response = self.client.get(url, {'content_type': self.ct.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)

    def test_filter_by_model_and_app_label(self):
        url = reverse('audit_log:audit-log-entries-list')
        response = self.client.get(url, {
            'model': 'partnerorganization',
            'app_label': 'partners',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)

    def test_filter_by_invalid_model_returns_empty(self):
        url = reverse('audit_log:audit-log-entries-list')
        response = self.client.get(url, {
            'model': 'nonexistent',
            'app_label': 'nonexistent',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

    def test_filter_by_user(self):
        other_user = UserFactory()
        url = reverse('audit_log:audit-log-entries-list')
        response = self.client.get(url, {'user': other_user.pk})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

    def test_unauthenticated_returns_403(self):
        self.client.logout()
        url = reverse('audit_log:audit-log-entries-list')
        response = self.client.get(url)
        self.assertIn(response.status_code, [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ])

    def test_response_contains_expected_fields(self):
        url = reverse('audit_log:audit-log-entries-list')
        response = self.client.get(url, {'object_id': '1', 'action': 'CREATE'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        entry = response.data['results'][0]
        self.assertIn('id', entry)
        self.assertIn('content_type', entry)
        self.assertIn('object_id', entry)
        self.assertIn('model_name', entry)
        self.assertIn('action', entry)
        self.assertIn('old_values', entry)
        self.assertIn('new_values', entry)
        self.assertIn('user', entry)
        self.assertIn('created', entry)
        self.assertEqual(entry['model_name'], 'partners.partnerorganization')

    def test_ordering_by_created_desc(self):
        url = reverse('audit_log:audit-log-entries-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        dates = [r['created'] for r in results]
        self.assertEqual(dates, sorted(dates, reverse=True))
