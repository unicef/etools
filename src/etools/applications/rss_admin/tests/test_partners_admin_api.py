from django.db import connection
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

import mock
from rest_framework import status

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.funds.tests.factories import FundsReservationHeaderFactory, FundsReservationItemFactory
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.models import Intervention
from etools.applications.partners.tests.factories import AgreementFactory, InterventionFactory, PartnerFactory
from etools.applications.reports.tests.factories import CountryProgrammeFactory, OfficeFactory, SectionFactory
from etools.applications.users.tests.factories import GroupFactory, RealmFactory, UserFactory
from etools.libraries.djangolib.fields import CURRENCY_LIST


@override_settings(RESTRICTED_ADMIN=False)
class TestRssAdminPartnersApi(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory(is_staff=True)
        cls.partner = PartnerFactory()
        cls.agreement = AgreementFactory(partner=cls.partner)
        cls.pd = InterventionFactory(agreement=cls.agreement, document_type=Intervention.PD)
        cls.spd = InterventionFactory(agreement=cls.agreement, document_type=Intervention.SPD)

    def test_list_partners(self):
        url = reverse('rss_admin:rss-admin-partners-list')
        response = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertTrue(any(row['id'] == self.partner.id for row in response.data))

    def test_filter_partners_by_rating(self):
        other_partner = PartnerFactory(rating='Medium')
        self.partner.rating = 'High'
        self.partner.save(update_fields=['rating'])

        url = reverse('rss_admin:rss-admin-partners-list')
        response = self.forced_auth_req('get', url, user=self.user, data={'rating': 'High'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [row['id'] for row in response.data]
        self.assertIn(self.partner.id, ids)
        self.assertNotIn(other_partner.id, ids)

    def test_filter_partners_by_organization_vendor_number(self):
        vendor_number = self.partner.organization.vendor_number
        url = reverse('rss_admin:rss-admin-partners-list')
        response = self.forced_auth_req('get', url, user=self.user, data={'organization__vendor_number': vendor_number})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [row['id'] for row in response.data]
        self.assertIn(self.partner.id, ids)

    def test_filter_partners_by_organization_id(self):
        url = reverse('rss_admin:rss-admin-partners-list')
        response = self.forced_auth_req('get', url, user=self.user, data={'organization': self.partner.organization.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [row['id'] for row in response.data]
        self.assertIn(self.partner.id, ids)

    def test_filter_partners_hidden_flag(self):
        hidden_partner = PartnerFactory(hidden=True)
        visible_partner = PartnerFactory(hidden=False)
        url = reverse('rss_admin:rss-admin-partners-list')
        resp_hidden = self.forced_auth_req('get', url, user=self.user, data={'hidden': True})
        self.assertEqual(resp_hidden.status_code, status.HTTP_200_OK)
        ids_hidden = [row['id'] for row in resp_hidden.data]
        self.assertIn(hidden_partner.id, ids_hidden)
        self.assertNotIn(visible_partner.id, ids_hidden)

        resp_visible = self.forced_auth_req('get', url, user=self.user, data={'hidden': False})
        self.assertEqual(resp_visible.status_code, status.HTTP_200_OK)
        ids_visible = [row['id'] for row in resp_visible.data]
        self.assertIn(visible_partner.id, ids_visible)
        self.assertNotIn(hidden_partner.id, ids_visible)

    def test_filter_partners_types_cso_and_ordering(self):
        p_type1 = PartnerFactory(organization__name='Zebra Institute')
        p_type1.organization.organization_type = 'Government'
        p_type1.organization.cso_type = 'Academic Institution'
        p_type1.organization.save()

        p_type2 = PartnerFactory(organization__name='Alpha Institute')
        p_type2.organization.organization_type = 'Government'
        p_type2.organization.cso_type = 'Academic Institution'
        p_type2.organization.save()

        url = reverse('rss_admin:rss-admin-partners-list')
        resp = self.forced_auth_req('get', url, user=self.user, data={
            'partner_types': 'Government',
            'cso_types': 'Academic Institution',
            'ordering': 'organization__name',
        })

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        names = [row['name'] for row in resp.data]
        self.assertEqual(names, sorted(names))

    def test_retrieve_partner(self):
        self.partner.refresh_from_db()
        url = reverse('rss_admin:rss-admin-partners-detail', kwargs={'pk': self.partner.pk})
        response = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.partner.id)
        self.assertEqual(response.data['name'], self.partner.organization.name)
        self.assertEqual(response.data['vendor_number'], self.partner.organization.vendor_number)
        # short_name may be blank/null by default; just ensure key exists
        self.assertTrue('short_name' in response.data)
        self.assertEqual(response.data['email'], self.partner.email)
        self.assertEqual(response.data['phone_number'], self.partner.phone_number)
        self.assertEqual(response.data['street_address'], self.partner.street_address)
        self.assertEqual(response.data['city'], self.partner.city)
        self.assertEqual(response.data['postal_code'], self.partner.postal_code)
        self.assertEqual(response.data['country'], self.partner.country)
        self.assertEqual(response.data['rating'], self.partner.rating)
        self.assertEqual(response.data['basis_for_risk_rating'], self.partner.basis_for_risk_rating)
        self.assertTrue('partner_type' in response.data)
        self.assertTrue('hact_risk_rating' in response.data)
        self.assertEqual(response.data['hact_risk_rating'], self.partner.rating)
        self.assertTrue('sea_risk_rating' in response.data)
        self.assertEqual(response.data['sea_risk_rating'], self.partner.sea_risk_rating_name)
        self.assertTrue('psea_last_assessment_date' in response.data)
        self.assertTrue('lead_office' in response.data)
        self.assertTrue('lead_office_name' in response.data)
        self.assertTrue('lead_section' in response.data)
        self.assertTrue('lead_section_name' in response.data)

    def test_create_partner(self):
        url = reverse('rss_admin:rss-admin-partners-list')
        new_org = OrganizationFactory()
        payload = {
            'organization': new_org.id,
        }
        response = self.forced_auth_req('post', url, user=self.user, data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)

    def test_update_partner(self):
        url = reverse('rss_admin:rss-admin-partners-detail', kwargs={'pk': self.partner.pk})
        payload = {
            'organization': self.partner.organization.id,
            'email': 'updated@example.com'
        }
        response = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'updated@example.com')

    def test_delete_partner(self):
        partner = PartnerFactory()
        url = reverse('rss_admin:rss-admin-partners-detail', kwargs={'pk': partner.pk})
        response = self.forced_auth_req('delete', url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_list_agreements(self):
        url = reverse('rss_admin:rss-admin-agreements-list')
        response = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(any(row['id'] == self.agreement.id for row in response.data))

    def test_partner_psea_date_serialization_date_only(self):
        # ensure datetime field is serialized as YYYY-MM-DD
        self.partner.psea_assessment_date = timezone.now()
        self.partner.save()
        url = reverse('rss_admin:rss-admin-partners-list')
        response = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        row = next(r for r in response.data if r['id'] == self.partner.id)
        self.assertEqual(row['psea_last_assessment_date'], timezone.now().date().isoformat())

    def test_list_pds(self):
        url = reverse('rss_admin:rss-admin-programme-documents-list')
        response = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [
            row['id'] for row in (
                response.data if isinstance(response.data, list) else response.data.get('results', [])
            )
            if row.get('document_type') == Intervention.PD
        ]
        self.assertIn(self.pd.id, ids)

    def test_list_spds(self):
        url = reverse('rss_admin:rss-admin-programme-documents-list')
        response = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [
            row['id'] for row in (
                response.data if isinstance(response.data, list) else response.data.get('results', [])
            )
            if row.get('document_type') == Intervention.SPD
        ]
        self.assertIn(self.spd.id, ids)

    def test_filter_programme_documents_by_status(self):
        self.pd.status = Intervention.ACTIVE
        self.pd.save(update_fields=['status'])
        url = reverse('rss_admin:rss-admin-programme-documents-list')
        resp = self.forced_auth_req('get', url, user=self.user, data={'status': Intervention.ACTIVE})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data if isinstance(resp.data, list) else resp.data.get('results', [])
        ids = [row['id'] for row in results]
        self.assertIn(self.pd.id, ids)

    def test_filter_programme_documents_by_agreement(self):
        url = reverse('rss_admin:rss-admin-programme-documents-list')
        resp = self.forced_auth_req('get', url, user=self.user, data={'agreement': self.agreement.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data if isinstance(resp.data, list) else resp.data.get('results', [])
        ids = [row['id'] for row in results]
        self.assertIn(self.pd.id, ids)
        self.assertIn(self.spd.id, ids)

    def test_filter_programme_documents_by_partner(self):
        url = reverse('rss_admin:rss-admin-programme-documents-list')
        resp = self.forced_auth_req('get', url, user=self.user, data={'agreement__partner': self.partner.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data if isinstance(resp.data, list) else resp.data.get('results', [])
        ids = [row['id'] for row in results]
        self.assertIn(self.pd.id, ids)
        self.assertIn(self.spd.id, ids)

    def test_filter_programme_documents_by_document_type(self):
        url = reverse('rss_admin:rss-admin-programme-documents-list')
        resp = self.forced_auth_req('get', url, user=self.user, data={'document_type': Intervention.PD})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data if isinstance(resp.data, list) else resp.data.get('results', [])
        ids = [row['id'] for row in results]
        self.assertIn(self.pd.id, ids)
        self.assertNotIn(self.spd.id, ids)

    def test_filter_programme_documents_donors_grants(self):
        frh = FundsReservationHeaderFactory(intervention=self.pd)
        fri = FundsReservationItemFactory(fund_reservation=frh)
        fri.donor = 'Asian Development Bank'
        fri.grant_number = 'GE180013'
        fri.save()

        url = reverse('rss_admin:rss-admin-programme-documents-list')
        resp = self.forced_auth_req('get', url, user=self.user, data={'donors': 'Asian Development Bank'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data if isinstance(resp.data, list) else resp.data.get('results', [])
        ids = [row['id'] for row in results]
        self.assertIn(self.pd.id, ids)

        resp2 = self.forced_auth_req('get', url, user=self.user, data={'grants': 'GE180013'})
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        results2 = resp2.data if isinstance(resp2.data, list) else resp2.data.get('results', [])
        ids2 = [row['id'] for row in results2]
        self.assertIn(self.pd.id, ids2)

    def test_filter_programme_documents_sections_offices_and_dates(self):
        section = SectionFactory()
        office = OfficeFactory()
        self.pd.sections.add(section)
        self.pd.offices.add(office)
        self.pd.start = timezone.now().date()
        self.pd.end = timezone.now().date()
        self.pd.save()

        url = reverse('rss_admin:rss-admin-programme-documents-list')
        resp = self.forced_auth_req('get', url, user=self.user, data={
            'sections': section.id,
            'office': office.id,
            'start': self.pd.start.isoformat(),
            'end': self.pd.end.isoformat(),
            'end_after': self.pd.end.isoformat(),
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data if isinstance(resp.data, list) else resp.data.get('results', [])
        ids = [row['id'] for row in results]
        self.assertIn(self.pd.id, ids)

    def test_filter_programme_documents_editable_by_and_contingency_and_ordering(self):
        self.pd.unicef_court = True
        self.pd.contingency_pd = True
        self.pd.title = 'A Title'
        self.pd.save(update_fields=['unicef_court', 'contingency_pd', 'title'])

        other = InterventionFactory(agreement=self.agreement, document_type=Intervention.PD, title='Z Title')
        other.unicef_court = False
        other.contingency_pd = False
        other.save(update_fields=['unicef_court', 'contingency_pd'])

        url = reverse('rss_admin:rss-admin-programme-documents-list')
        resp = self.forced_auth_req('get', url, user=self.user, data={'editable_by': 'unicef', 'contingency_pd': True, 'ordering': 'title'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data if isinstance(resp.data, list) else resp.data.get('results', [])
        titles = [row['title'] for row in results]
        self.assertIn(self.pd.title, titles)
        self.assertTrue(titles == sorted(titles))

    def test_programme_documents_show_amendments(self):
        amended = InterventionFactory(agreement=self.agreement, document_type=Intervention.PD, in_amendment=True)
        url = reverse('rss_admin:rss-admin-programme-documents-list')
        resp_default = self.forced_auth_req('get', url, user=self.user)
        results_default = resp_default.data if isinstance(resp_default.data, list) else resp_default.data.get('results', [])
        self.assertNotIn(amended.id, [row['id'] for row in results_default])
        resp_include = self.forced_auth_req('get', url, user=self.user, data={'show_amendments': True})
        self.assertEqual(resp_include.status_code, status.HTTP_200_OK)
        results_include = resp_include.data if isinstance(resp_include.data, list) else resp_include.data.get('results', [])
        self.assertIn(amended.id, [row['id'] for row in results_include])

    def test_agreement_date_fields_are_date_strings(self):
        # Set agreement dates and ensure serializer returns YYYY-MM-DD
        today = timezone.now().date()
        self.agreement.start = today
        self.agreement.end = today
        self.agreement.signed_by_unicef_date = today
        self.agreement.signed_by_partner_date = today
        self.agreement.save()

        # list endpoint
        url = reverse('rss_admin:rss-admin-agreements-list')
        resp = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        row = next(r for r in resp.data if r['id'] == self.agreement.id)
        self.assertEqual(row['start'], today.isoformat())
        expected_end = self.agreement.country_programme.to_date.isoformat()
        self.assertEqual(row['end'], expected_end)
        self.assertEqual(row['signed_by_unicef_date'], today.isoformat())
        self.assertEqual(row['signed_by_partner_date'], today.isoformat())

    def test_patch_pd_title(self):
        url = reverse('rss_admin:rss-admin-programme-documents-detail', kwargs={'pk': self.pd.pk})
        resp = self.forced_auth_req('patch', url, user=self.user, data={'title': 'Updated PD Title'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['title'], 'Updated PD Title')

    def test_patch_spd_title(self):
        url = reverse('rss_admin:rss-admin-programme-documents-detail', kwargs={'pk': self.spd.pk})
        resp = self.forced_auth_req('patch', url, user=self.user, data={'title': 'Updated SPD Title'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['title'], 'Updated SPD Title')

    @mock.patch('etools.applications.rss_admin.views.send_pd_to_vision')
    def test_signed_triggers_vision_sync(self, mock_task):
        pd = InterventionFactory(agreement=self.agreement, document_type=Intervention.PD, status=Intervention.REVIEW)
        url = reverse('rss_admin:rss-admin-programme-documents-detail', kwargs={'pk': pd.pk})
        resp = self.forced_auth_req('patch', url, user=self.user, data={'status': Intervention.SIGNED})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # ensure task is queued with correct args
        self.assertTrue(mock_task.delay.called)
        args, kwargs = mock_task.delay.call_args
        self.assertEqual(args[1], pd.pk)

    # PD/SPD editing happens in Django admin, not via rss_admin endpoints

    def test_list_partners_paginated(self):
        url = reverse('rss_admin:rss-admin-partners-list')
        response = self.forced_auth_req('get', url, user=self.user, data={'page': 1, 'page_size': 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, dict)
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)
        self.assertIsInstance(response.data['results'], list)
        ids = [row['id'] for row in response.data['results']]
        self.assertTrue(self.partner.id in ids or response.data['count'] >= 1)

    def test_list_agreements_paginated(self):
        url = reverse('rss_admin:rss-admin-agreements-list')
        response = self.forced_auth_req('get', url, user=self.user, data={'page': 1, 'page_size': 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, dict)
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)
        self.assertIsInstance(response.data['results'], list)
        ids = [row['id'] for row in response.data['results']]
        self.assertTrue(self.agreement.id in ids or response.data['count'] >= 1)

    def test_filter_agreements_by_status(self):
        # create a second agreement with a different status
        other_agreement = AgreementFactory(partner=self.partner, status='draft')
        self.agreement.status = 'signed'
        self.agreement.save(update_fields=['status'])

        url = reverse('rss_admin:rss-admin-agreements-list')
        response = self.forced_auth_req('get', url, user=self.user, data={'status': 'signed'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [row['id'] for row in response.data]
        self.assertIn(self.agreement.id, ids)
        self.assertNotIn(other_agreement.id, ids)

    def test_filter_agreements_by_partner(self):
        # filter by partner id
        url = reverse('rss_admin:rss-admin-agreements-list')
        response = self.forced_auth_req('get', url, user=self.user, data={'partner': self.partner.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [row['id'] for row in response.data]
        self.assertIn(self.agreement.id, ids)

    def test_filter_agreements_by_type(self):
        self.agreement.agreement_type = 'PCA'
        self.agreement.save(update_fields=['agreement_type'])
        url = reverse('rss_admin:rss-admin-agreements-list')
        response = self.forced_auth_req('get', url, user=self.user, data={'agreement_type': 'PCA'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [row['id'] for row in response.data]
        self.assertIn(self.agreement.id, ids)

    def test_filter_agreements_cp_structures_dates_special_flags_and_ordering(self):
        cp = CountryProgrammeFactory()
        ag1 = AgreementFactory(partner=self.partner, country_programme=cp, status='draft', special_conditions_pca=True)
        ag1.start = timezone.now().date()
        ag1.end = timezone.now().date()
        ag1.save()

        url = reverse('rss_admin:rss-admin-agreements-list')
        resp = self.forced_auth_req('get', url, user=self.user, data={
            'cpStructures': cp.id,
            'status': 'draft',
            'special_conditions_pca': True,
            'start': ag1.start.isoformat(),
            'end': ag1.end.isoformat(),
            'ordering': 'partner_name',
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = [row['id'] for row in resp.data]
        self.assertIn(ag1.id, ids)

    def test_filter_agreements_by_number(self):
        url = reverse('rss_admin:rss-admin-agreements-list')
        response = self.forced_auth_req('get', url, user=self.user, data={'agreement_number': self.agreement.agreement_number})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [row['id'] for row in response.data]
        self.assertIn(self.agreement.id, ids)

    def test_retrieve_agreement_details(self):
        url = reverse('rss_admin:rss-admin-agreements-detail', kwargs={'pk': self.agreement.pk})
        response = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.agreement.id)
        self.assertEqual(response.data['agreement_number'], self.agreement.agreement_number)
        self.assertEqual(response.data['agreement_type'], self.agreement.agreement_type)
        self.assertEqual(response.data['status'], self.agreement.status)
        self.assertEqual(response.data['partner']['id'], self.partner.id)
        # start
        if self.agreement.start:
            self.assertEqual(response.data['start'], str(self.agreement.start))
        else:
            self.assertIsNone(response.data['start'])
        # end
        if self.agreement.end:
            self.assertEqual(response.data['end'], str(self.agreement.end))
        else:
            self.assertIsNone(response.data['end'])
        # officers
        expected_officer_ids = set(self.agreement.authorized_officers.values_list('id', flat=True))
        returned_officer_ids = set([o['id'] for o in response.data['authorized_officers']])
        self.assertEqual(returned_officer_ids, expected_officer_ids)
        # file url
        self.assertIsNone(response.data['attached_agreement_file'])
        # signature dates
        self.assertEqual(response.data['signed_by_unicef_date'], str(self.agreement.signed_by_unicef_date))
        self.assertEqual(response.data['signed_by_partner_date'], str(self.agreement.signed_by_partner_date))
        # partner signatory id
        self.assertEqual(response.data['partner_signatory'], self.agreement.partner_manager_id)

    def test_update_agreement_signature_dates(self):
        url = reverse('rss_admin:rss-admin-agreements-detail', kwargs={'pk': self.agreement.pk})
        payload = {
            'signed_by_unicef_date': '2024-01-02',
            'signed_by_partner_date': '2024-01-03'
        }
        response = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['signed_by_unicef_date'], '2024-01-02')
        self.assertEqual(response.data['signed_by_partner_date'], '2024-01-03')

    def test_update_agreement_signature_single_field(self):
        url = reverse('rss_admin:rss-admin-agreements-detail', kwargs={'pk': self.agreement.pk})
        payload = {'signed_by_unicef_date': '2024-02-10'}
        response = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['signed_by_unicef_date'], '2024-02-10')

    def test_patch_attachment_officers_and_signature(self):
        url = reverse('rss_admin:rss-admin-agreements-detail', kwargs={'pk': self.agreement.pk})
        officer = UserFactory()
        attachment = AttachmentFactory(file="upload.pdf")
        payload = {
            'signed_by_unicef_date': '2025-10-15',
            'attachment': attachment.id,
            'authorized_officers_ids': [officer.id],
        }
        response = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        # officers changed
        returned_officer_ids = set([o['id'] for o in response.data['authorized_officers']])
        self.assertEqual(returned_officer_ids, {officer.id})
        # signature date changed
        self.assertEqual(response.data['signed_by_unicef_date'], '2025-10-15')
        # attachment linked: URL comes via 'attachment'; FileField remains unset
        self.assertTrue(response.data['attachment'])

    def test_retrieve_agreement_details_with_attached_agreement_file(self):
        # 1) Simulate prior upload by creating an attachment with a file
        attachment = AttachmentFactory(file="agreement.pdf")
        # 2) Link to agreement (attachment field) and assert URL present in response
        url = reverse('rss_admin:rss-admin-agreements-detail', kwargs={'pk': self.agreement.pk})
        resp = self.forced_auth_req('patch', url, user=self.user, data={'attachment': attachment.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertTrue(resp.data['attachment'])

    def test_update_agreement_authorized_officers(self):
        url = reverse('rss_admin:rss-admin-agreements-detail', kwargs={'pk': self.agreement.pk})
        officer1 = UserFactory()
        officer2 = UserFactory()
        payload = {'authorized_officers_ids': [officer1.id, officer2.id]}
        response = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(len(response.data['authorized_officers']), 2)

    def test_agreements_permission_denied_for_non_staff(self):
        non_staff_user = UserFactory(is_staff=False)
        url = reverse('rss_admin:rss-admin-agreements-list')
        response = self.forced_auth_req('get', url, user=non_staff_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_agreements_search_by_agreement_number(self):
        # ensure our created agreement is retrievable via search
        url = reverse('rss_admin:rss-admin-agreements-list')
        response = self.forced_auth_req('get', url, user=self.user, data={'search': self.agreement.agreement_number})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [row['id'] for row in response.data]
        self.assertIn(self.agreement.id, ids)

    def test_bulk_close_success(self):
        pd1 = InterventionFactory(
            agreement=self.agreement,
            document_type=Intervention.PD,
            status=Intervention.ENDED,
        )
        pd2 = InterventionFactory(
            agreement=self.agreement,
            document_type=Intervention.PD,
            status=Intervention.ENDED,
        )
        pd3 = InterventionFactory(
            agreement=self.agreement,
            document_type=Intervention.PD,
            status=Intervention.ENDED,
        )
        # ensure validator passes end date and final review
        for pd in (pd1, pd2, pd3):
            pd.end = pd.created.date()
            pd.final_review_approved = True
            pd.save()

        url = reverse('rss_admin:rss-admin-programme-documents-bulk-close')
        payload = {'programme_documents': [pd1.id, pd2.id, pd3.id]}
        resp = self.forced_auth_req('put', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        closed = set(resp.data['closed_ids'])
        self.assertTrue(set([pd1.id, pd2.id, pd3.id]).issubset(closed))
        for pd in (pd1, pd2, pd3):
            pd.refresh_from_db()
            self.assertEqual(pd.status, Intervention.CLOSED)

    def test_bulk_close_rejects_non_pd(self):
        spd = InterventionFactory(
            agreement=self.agreement,
            document_type=Intervention.SPD,
            status=Intervention.ENDED,
        )
        url = reverse('rss_admin:rss-admin-programme-documents-bulk-close')
        payload = {'programme_documents': [spd.id]}
        resp = self.forced_auth_req('put', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bulk_close_errors_when_not_ended(self):
        pd = InterventionFactory(
            agreement=self.agreement,
            document_type=Intervention.PD,
            status=Intervention.ACTIVE,
        )
        url = reverse('rss_admin:rss-admin-programme-documents-bulk-close')
        payload = {'programme_documents': [pd.id]}
        resp = self.forced_auth_req('put', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(any(e['id'] == pd.id for e in resp.data['errors']))

    def test_assign_frs_to_pd(self):
        fr1 = FundsReservationHeaderFactory(intervention=None)
        fr2 = FundsReservationHeaderFactory(intervention=None)

        url = reverse('rss_admin:rss-admin-programme-documents-assign-frs', kwargs={'pk': self.pd.pk})
        payload = {'frs': [fr1.id, fr2.id]}
        resp = self.forced_auth_req('post', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        # 'frs' returns a list of FR ids
        self.assertCountEqual(resp.data['frs'], [fr1.id, fr2.id])
        # 'frs_details.frs' returns FR objects; verify ids match
        returned_ids = [fr['id'] for fr in resp.data['frs_details']['frs']]
        self.assertCountEqual(returned_ids, [fr1.id, fr2.id])

    def test_set_currency_on_pd(self):
        currency = CURRENCY_LIST[0]
        url = reverse('rss_admin:rss-admin-programme-documents-set-currency', kwargs={'pk': self.pd.pk})
        resp = self.forced_auth_req('post', url, user=self.user, data={'currency': currency})
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data['planned_budget']['currency'], currency)

    def test_set_currency_invalid(self):
        url = reverse('rss_admin:rss-admin-programme-documents-set-currency', kwargs={'pk': self.pd.pk})
        resp = self.forced_auth_req('post', url, user=self.user, data={'currency': 'XXX'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch('etools.applications.rss_admin.views.send_pd_to_vision')
    def test_send_to_vision_action(self, mock_task):
        url = reverse('rss_admin:rss-admin-programme-documents-send-to-vision', kwargs={'pk': self.pd.pk})
        resp = self.forced_auth_req('post', url, user=self.user)
        self.assertEqual(resp.status_code, status.HTTP_202_ACCEPTED)
        self.assertTrue(mock_task.delay.called)
        args, _kwargs = mock_task.delay.call_args
        self.assertEqual(args[1], self.pd.pk)

    @override_settings(RESTRICTED_ADMIN=True)
    def test_access_allowed_for_rss_admin_realm(self):
        user = UserFactory(is_staff=False)
        group = GroupFactory(name='Rss Admin')
        RealmFactory(user=user, country=connection.tenant, group=group, is_active=True)

        url = reverse('rss_admin:rss-admin-partners-list')
        response = self.forced_auth_req('get', url, user=user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @override_settings(RESTRICTED_ADMIN=True)
    def test_access_denied_without_rss_admin_realm(self):
        user = UserFactory(is_staff=False)
        # no realm added for this user in current tenant with the required group
        url = reverse('rss_admin:rss-admin-partners-list')
        response = self.forced_auth_req('get', url, user=user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
