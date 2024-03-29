# from django.db import connection
# from django.utils import timezone
#
# from etools.applications.core.tests.cases import BaseTenantTestCase
# from etools.applications.partners.tests.factories import InterventionFactory

# TODO clean up: endpoint removed in prp'
# class TestInterventionPartnerSyncSignal(BaseTenantTestCase):
#     def test_intervention_sync_called(self, sync_task_mock):
#         intervention = InterventionFactory(date_sent_to_partner=None)
#         sync_task_mock.assert_not_called()
#
#         intervention.date_sent_to_partner = timezone.now()
#         intervention.save()
#         sync_task_mock.assert_called_with(connection.tenant.name, intervention.agreement.partner_id)
#
#     def test_intervention_sync_not_called_on_save(self, sync_task_mock):
#         intervention = InterventionFactory(date_sent_to_partner=None)
#         sync_task_mock.assert_not_called()
#
#         intervention.start = timezone.now().date()
#         intervention.save()
#         sync_task_mock.assert_not_called()
#
#     def test_intervention_sync_called_on_create(self, sync_task_mock):
#         intervention = InterventionFactory(date_sent_to_partner=timezone.now())
#         sync_task_mock.assert_called_with(connection.tenant.name, intervention.agreement.partner_id)


# TODO clean up: endpoint removed in prp'
# class TestInterventionPartnerSyncTask(BaseTenantTestCase):
#     @override_settings(PRP_API_ENDPOINT='http://example.com/api/')
#     @patch(
#         'etools.applications.partners.prp_api.requests.post',
#         return_value=namedtuple('Response', ['status_code', 'text'])(200, '{}')
#     )
#     def test_request_to_prp_sent(self, request_mock):
#         intervention = InterventionFactory(date_sent_to_partner=None)
#
#         UserFactory(
#             profile__organization=intervention.agreement.partner.organization, realms__data=['IP Viewer']
#         )
#         request_mock.assert_not_called()
#
#         sync_partner_to_prp(connection.tenant.name, intervention.agreement.partner_id)
#         request_mock.assert_called()
#
#
# class TestPartnerStaffMembersImportTask(BaseTenantTestCase):
#     @override_settings(PRP_API_ENDPOINT='http://example.com/api/')
#     @patch(
#         'etools.applications.partners.prp_api.requests.post',
#         return_value=namedtuple('Response', ['status_code', 'text'])(200, '{}')
#     )
#     def test_request_to_prp_sent(self, request_mock):
#         intervention = InterventionFactory(date_sent_to_partner=None)
#         request_mock.assert_not_called()
#
#         sync_partner_to_prp(connection.tenant.name, intervention.agreement.partner_id)
#         request_mock.assert_called()
#
#     @classmethod
#     def setUpTestData(cls):
#         cls.partner = PartnerFactory()
#         cls.staff_member = UserFactory(
#             profile__organization=cls.partner.organization,
#             realms__data=['IP Viewer']
#         )
#         cls.prp_partners_export_response_data = {
#             'count': 2,
#             'results': [
#                 {
#                     'id': 1, 'external_id': str(cls.partner.id),
#                     'unicef_vendor_number': cls.partner.vendor_number, 'name': cls.partner.name
#                 },
#                 {'id': 2, 'external_id': -1, 'unicef_vendor_number': '', 'name': 'Unknown Co'},
#             ]
#         }
#         cls.prp_partner_staff_members_response_data = {
#             'count': 2,
#             'results': [
#                 {
#                     'email': cls.staff_member.email.upper(), 'title': cls.staff_member.profile.job_title,
#                     'first_name': cls.staff_member.first_name, 'last_name': cls.staff_member.last_name,
#                     'phone_number': cls.staff_member.profile.phone_number, 'is_active': True,
#                 },
#                 {
#                     'email': 'anonymous@example.com', 'title': 'Unknown User',
#                     'first_name': 'Unknown', 'last_name': 'User',
#                     'phone_number': '-995122341', 'is_active': True,
#                 },
#             ]
#         }
#
#         def get_prp_export_response(*args, **kwargs):
#             url = kwargs['url']
#             if '/unicef/pmp/export/partners/?page=' in url:
#                 return namedtuple('Response', ['status_code', 'text'])(
#                     200, json.dumps(cls.prp_partners_export_response_data)
#                 )
#             elif '/staff-members/?page=' in url:
#                 return namedtuple('Response', ['status_code', 'text'])(
#                     200, json.dumps(cls.prp_partner_staff_members_response_data)
#                 )
#             else:
#                 return namedtuple('Response', ['status_code', 'text'])(404, '{}')
#         cls.get_prp_export_response = get_prp_export_response
#
#     @override_settings(PRP_API_ENDPOINT='http://example.com/api/')
#     @patch('etools.applications.partners.prp_api.requests.get')
#     def test_sync(self, request_mock):
#         self.assertEqual(self.partner.active_staff_members.count(), 1)
#
#         self.staff_member.active = False
#         self.staff_member.save()
#
#         request_mock.side_effect = self.get_prp_export_response
#         sync_partners_staff_members_from_prp()
#
#         self.assertTrue(self.partner.active_staff_members.count(), 2)
#
#         # check second user created
#         self.assertTrue(User.objects.filter(email='anonymous@example.com').exists())
#
#         # check first user was updated
#         self.staff_member.refresh_from_db()
#         self.assertTrue(self.staff_member.is_active)
#         # and email was not changed even if provided in uppercase
#         self.assertNotEqual(self.staff_member.email, self.staff_member.email.upper())
