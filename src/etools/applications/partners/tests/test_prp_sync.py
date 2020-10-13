import json
from collections import namedtuple

from django.db import connection
from django.utils import timezone

from mock import patch

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import PartnerStaffMember
from etools.applications.partners.tasks import sync_partner_to_prp, sync_partners_staff_members_from_prp
from etools.applications.partners.tests.factories import InterventionFactory, PartnerFactory, PartnerStaffFactory
from etools.applications.users.tests.factories import UserFactory


class TestInterventionPartnerSyncSignal(BaseTenantTestCase):
    @patch('etools.applications.partners.signals.sync_partner_to_prp.delay')
    def test_intervention_sync_called(self, sync_task_mock):
        intervention = InterventionFactory()
        sync_task_mock.assert_not_called()

        intervention.date_sent_to_partner = timezone.now()
        intervention.save()
        sync_task_mock.assert_called_with(connection.tenant.name, intervention.agreement.partner_id)

    @patch('etools.applications.partners.signals.sync_partner_to_prp.delay')
    def test_intervention_sync_not_called_on_save(self, sync_task_mock):
        intervention = InterventionFactory()
        sync_task_mock.assert_not_called()

        intervention.start = timezone.now()
        intervention.save()
        sync_task_mock.assert_not_called()

    @patch('etools.applications.partners.signals.sync_partner_to_prp.delay')
    def test_intervention_sync_called_on_create(self, sync_task_mock):
        intervention = InterventionFactory(date_sent_to_partner=timezone.now())
        sync_task_mock.assert_called_with(connection.tenant.name, intervention.agreement.partner_id)


class TestInterventionPartnerSyncTask(BaseTenantTestCase):
    @patch(
        'etools.applications.partners.prp_api.requests.post',
        return_value=namedtuple('Response', ['status_code', 'text'])(200, '{}')
    )
    def test_request_to_prp_sent(self, request_mock):
        intervention = InterventionFactory()
        request_mock.assert_not_called()

        sync_partner_to_prp(connection.tenant.name, intervention.agreement.partner_id)
        request_mock.assert_called()


class TestPartnerStaffMembersImportTask(BaseTenantTestCase):
    @patch(
        'etools.applications.partners.prp_api.requests.post',
        return_value=namedtuple('Response', ['status_code', 'text'])(200, '{}')
    )
    def test_request_to_prp_sent(self, request_mock):
        intervention = InterventionFactory()
        request_mock.assert_not_called()

        sync_partner_to_prp(connection.tenant.name, intervention.agreement.partner_id)
        request_mock.assert_called()

    @classmethod
    def setUpTestData(cls):
        cls.partner = PartnerFactory(staff_members=[])
        cls.staff_member = PartnerStaffFactory(partner=cls.partner)
        cls.staff_member_user = UserFactory(profile__partner_staff_member=cls.staff_member.id)

        cls.prp_partners_export_response_data = {
            'count': 2,
            'results': [
                {
                    'id': 1, 'external_id': str(cls.partner.id),
                    'unicef_vendor_number': cls.partner.vendor_number, 'name': cls.partner.name
                },
                {'id': 2, 'external_id': -1, 'unicef_vendor_number': '', 'name': 'Unknown Co'},
            ]
        }
        cls.prp_partner_staff_members_response_data = {
            'count': 2,
            'results': [
                {
                    'email': cls.staff_member.email.upper(), 'title': cls.staff_member.title,
                    'first_name': cls.staff_member.first_name, 'last_name': cls.staff_member.last_name,
                    'phone_number': cls.staff_member.phone, 'is_active': True,
                },
                {
                    'email': 'anonymous@example.com', 'title': 'Unknown User',
                    'first_name': 'Unknown', 'last_name': 'User',
                    'phone_number': '-995122341', 'is_active': True,
                },
            ]
        }

        def get_prp_export_response(*args, **kwargs):
            url = kwargs['url']
            if '/unicef/pmp/export/partners/?page=' in url:
                return namedtuple('Response', ['status_code', 'text'])(
                    200, json.dumps(cls.prp_partners_export_response_data)
                )
            elif '/staff-members/?page=' in url:
                return namedtuple('Response', ['status_code', 'text'])(
                    200, json.dumps(cls.prp_partner_staff_members_response_data)
                )
            else:
                return namedtuple('Response', ['status_code', 'text'])(404, '{}')
        cls.get_prp_export_response = get_prp_export_response

    @patch('etools.applications.partners.prp_api.requests.get')
    def test_sync(self, request_mock):
        self.assertEqual(self.partner.staff_members.count(), 1)

        self.staff_member.active = False
        self.staff_member.save()

        request_mock.side_effect = self.get_prp_export_response
        sync_partners_staff_members_from_prp()

        self.assertTrue(self.partner.staff_members.count(), 2)

        # check second user created
        self.assertTrue(PartnerStaffMember.objects.filter(email='anonymous@example.com', partner=self.partner).exists())

        # check first user was updated
        self.staff_member.refresh_from_db()
        self.assertTrue(self.staff_member.active)
        # and email was not changed even if provided in uppercase
        self.assertNotEqual(self.staff_member.email, self.staff_member.email.upper())