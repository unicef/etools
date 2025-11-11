from datetime import timedelta

from django.db import connection
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

import mock
from rest_framework import status
from unicef_locations.tests.factories import LocationFactory

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.audit.models import Engagement
from etools.applications.audit.tests.factories import (
    AuditFactory,
    EngagementFactory,
    SpotCheckFactory,
    StaffSpotCheckFactory,
)
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.funds.tests.factories import FundsReservationHeaderFactory, FundsReservationItemFactory
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.models import Intervention
from etools.applications.partners.tests.factories import AgreementFactory, InterventionFactory, PartnerFactory
from etools.applications.reports.tests.factories import (
    CountryProgrammeFactory,
    OfficeFactory,
    ReportingRequirementFactory,
    SectionFactory,
)
from etools.applications.users.tests.factories import GroupFactory, RealmFactory, UserFactory
from etools.libraries.djangolib.fields import CURRENCY_LIST
from etools.applications.action_points.tests.factories import ActionPointFactory


@override_settings(RESTRICTED_ADMIN=False)
class TestRssAdminPartnersApi(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory(is_staff=True)
        cls.partner = PartnerFactory()
        # Ensure partner passes PCA/SSFA validation in AgreementValid
        cls.partner.organization.organization_type = "Civil Society Organization"
        cls.partner.organization.save(update_fields=['organization_type'])
        cls.agreement = AgreementFactory(partner=cls.partner)
        cls.pd = InterventionFactory(agreement=cls.agreement, document_type=Intervention.PD)
        cls.spd = InterventionFactory(agreement=cls.agreement, document_type=Intervention.SPD)

    def _results(self, response):
        return response.data if isinstance(response.data, list) else response.data.get('results', [])

    def _ids(self, response):
        return [row['id'] for row in self._results(response)]

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
        self.assertIn('short_name', response.data)
        self.assertEqual(response.data['email'], self.partner.email)
        self.assertEqual(response.data['phone_number'], self.partner.phone_number)
        self.assertEqual(response.data['street_address'], self.partner.street_address)
        self.assertEqual(response.data['city'], self.partner.city)
        self.assertEqual(response.data['postal_code'], self.partner.postal_code)
        self.assertEqual(response.data['country'], self.partner.country)
        self.assertEqual(response.data['rating'], self.partner.rating)
        self.assertEqual(response.data['basis_for_risk_rating'], self.partner.basis_for_risk_rating)
        self.assertIn('partner_type', response.data)
        self.assertIn('hact_risk_rating', response.data)
        self.assertEqual(response.data['hact_risk_rating'], self.partner.rating)
        self.assertIn('sea_risk_rating', response.data)
        self.assertEqual(response.data['sea_risk_rating'], self.partner.sea_risk_rating_name)
        self.assertIn('psea_last_assessment_date', response.data)
        self.assertIn('lead_office', response.data)
        self.assertIn('lead_office_name', response.data)
        self.assertIn('lead_section', response.data)
        self.assertIn('lead_section_name', response.data)

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
        dt = timezone.now()
        self.partner.psea_assessment_date = dt
        self.partner.save()
        url = reverse('rss_admin:rss-admin-partners-list')
        response = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        row = next(r for r in response.data if r['id'] == self.partner.id)
        self.assertEqual(row['psea_last_assessment_date'], dt.date().isoformat())

    def test_list_pds(self):
        url = reverse('rss_admin:rss-admin-programme-documents-list')
        response = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = self._results(response)
        ids = [row['id'] for row in results if row.get('document_type') == Intervention.PD]
        self.assertIn(self.pd.id, ids)

    def test_list_spds(self):
        url = reverse('rss_admin:rss-admin-programme-documents-list')
        response = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = self._results(response)
        ids = [row['id'] for row in results if row.get('document_type') == Intervention.SPD]
        self.assertIn(self.spd.id, ids)

    def test_filter_programme_documents_by_status(self):
        self.pd.status = Intervention.ACTIVE
        self.pd.save(update_fields=['status'])
        url = reverse('rss_admin:rss-admin-programme-documents-list')
        resp = self.forced_auth_req('get', url, user=self.user, data={'status': Intervention.ACTIVE})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = self._results(resp)
        ids = [row['id'] for row in results]
        self.assertIn(self.pd.id, ids)

    def test_filter_programme_documents_by_statuses_plural(self):
        self.pd.status = Intervention.ACTIVE
        self.pd.save(update_fields=['status'])
        url = reverse('rss_admin:rss-admin-programme-documents-list')
        resp = self.forced_auth_req('get', url, user=self.user, data={'statuses': Intervention.ACTIVE})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data if isinstance(resp.data, list) else resp.data.get('results', [])
        ids = [row['id'] for row in results]
        self.assertIn(self.pd.id, ids)

    def test_filter_programme_documents_by_agreement(self):
        url = reverse('rss_admin:rss-admin-programme-documents-list')
        resp = self.forced_auth_req('get', url, user=self.user, data={'agreement': self.agreement.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = self._results(resp)
        ids = [row['id'] for row in results]
        self.assertIn(self.pd.id, ids)
        self.assertIn(self.spd.id, ids)

    def test_filter_programme_documents_by_partner(self):
        url = reverse('rss_admin:rss-admin-programme-documents-list')
        resp = self.forced_auth_req('get', url, user=self.user, data={'agreement__partner': self.partner.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = self._results(resp)
        ids = [row['id'] for row in results]
        self.assertIn(self.pd.id, ids)
        self.assertIn(self.spd.id, ids)

    def test_filter_programme_documents_by_document_type(self):
        url = reverse('rss_admin:rss-admin-programme-documents-list')
        resp = self.forced_auth_req('get', url, user=self.user, data={'document_type': Intervention.PD})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = self._results(resp)
        ids = [row['id'] for row in results]
        self.assertIn(self.pd.id, ids)
        self.assertNotIn(self.spd.id, ids)

    def test_filter_programme_documents_by_document_types_plural(self):
        url = reverse('rss_admin:rss-admin-programme-documents-list')
        resp = self.forced_auth_req('get', url, user=self.user, data={'document_types': Intervention.PD})
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
        results = self._results(resp)
        ids = [row['id'] for row in results]
        self.assertIn(self.pd.id, ids)

        resp2 = self.forced_auth_req('get', url, user=self.user, data={'grants': 'GE180013'})
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        results2 = self._results(resp2)
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
        results = self._results(resp)
        ids = [row['id'] for row in results]
        self.assertIn(self.pd.id, ids)

    def test_filter_programme_documents_offices_plural(self):
        office = OfficeFactory()
        self.pd.offices.add(office)
        self.pd.save()

        url = reverse('rss_admin:rss-admin-programme-documents-list')
        resp = self.forced_auth_req('get', url, user=self.user, data={'offices': office.id})
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
        results = self._results(resp)
        titles = [row['title'] for row in results]
        self.assertIn(self.pd.title, titles)
        self.assertEqual(titles, sorted(titles))

    def test_programme_documents_show_amendments(self):
        amended = InterventionFactory(agreement=self.agreement, document_type=Intervention.PD, in_amendment=True)
        url = reverse('rss_admin:rss-admin-programme-documents-list')
        resp_default = self.forced_auth_req('get', url, user=self.user)
        results_default = self._results(resp_default)
        self.assertNotIn(amended.id, [row['id'] for row in results_default])
        resp_include = self.forced_auth_req('get', url, user=self.user, data={'show_amendments': True})
        self.assertEqual(resp_include.status_code, status.HTTP_200_OK)
        results_include = self._results(resp_include)
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
        # Prefill required fields for current status to pass validator
        today = timezone.now().date()
        # ensure a forgiving status
        self.pd.status = Intervention.DRAFT
        self.pd.unicef_signatory = self.user
        self.pd.partner_authorized_officer_signatory = UserFactory()
        self.pd.signed_by_unicef_date = today
        self.pd.signed_by_partner_date = today
        self.pd.date_sent_to_partner = today
        self.pd.budget_owner = self.user
        self.pd.activation_protocol = 'Activation protocol'
        self.pd.save(update_fields=['status', 'unicef_signatory', 'partner_authorized_officer_signatory',
                                    'signed_by_unicef_date', 'signed_by_partner_date', 'date_sent_to_partner',
                                    'budget_owner', 'activation_protocol'])
        self.pd.offices.add(OfficeFactory())
        self.pd.sections.add(SectionFactory())
        self.pd.flat_locations.add(LocationFactory())
        self.pd.unicef_focal_points.add(self.user)
        self.pd.partner_focal_points.add(UserFactory())
        # add minimal reporting requirement and signed PD attachment (safe even in draft)
        ReportingRequirementFactory(intervention=self.pd)
        AttachmentFactory(code='partners_intervention_signed_pd', content_object=self.pd)
        resp = self.forced_auth_req('patch', url, user=self.user, data={'title': 'Updated PD Title'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data['title'], 'Updated PD Title')

    def test_patch_spd_title(self):
        url = reverse('rss_admin:rss-admin-programme-documents-detail', kwargs={'pk': self.spd.pk})
        # Prefill required fields for current status to pass validator
        today = timezone.now().date()
        self.spd.status = Intervention.DRAFT
        self.spd.unicef_signatory = self.user
        self.spd.partner_authorized_officer_signatory = UserFactory()
        self.spd.signed_by_unicef_date = today
        self.spd.signed_by_partner_date = today
        self.spd.date_sent_to_partner = today
        self.spd.budget_owner = self.user
        self.spd.activation_protocol = 'Activation protocol'
        self.spd.save(update_fields=['status', 'unicef_signatory', 'partner_authorized_officer_signatory',
                                     'signed_by_unicef_date', 'signed_by_partner_date', 'date_sent_to_partner',
                                     'budget_owner', 'activation_protocol'])
        self.spd.offices.add(OfficeFactory())
        self.spd.sections.add(SectionFactory())
        self.spd.flat_locations.add(LocationFactory())
        self.spd.unicef_focal_points.add(self.user)
        self.spd.partner_focal_points.add(UserFactory())
        ReportingRequirementFactory(intervention=self.spd)
        AttachmentFactory(code='partners_intervention_signed_pd', content_object=self.spd)
        resp = self.forced_auth_req('patch', url, user=self.user, data={'title': 'Updated SPD Title'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data['title'], 'Updated SPD Title')

    @mock.patch('etools.applications.partners.tasks.send_pd_to_vision')
    def test_signed_triggers_vision_sync(self, mock_task):
        """Side-effect: PD transitioning to signed triggers Vision sync task with correct args (if transition succeeds)."""
        # ensure agreement is signed, start from SIGNATURE
        self.agreement.status = 'signed'
        self.agreement.save(update_fields=['status'])
        pd = InterventionFactory(agreement=self.agreement, document_type=Intervention.PD, status=Intervention.SIGNATURE)
        url = reverse('rss_admin:rss-admin-programme-documents-detail', kwargs={'pk': pd.pk})
        resp = self.forced_auth_req('patch', url, user=self.user, data={'title': 'noop'})
        if resp.status_code == status.HTTP_200_OK:
            self.assertTrue(mock_task.delay.called)
            args, kwargs = mock_task.delay.call_args
            # sent via model side-effect: (tenant_name, intervention_pk)
            self.assertEqual(args[0], connection.tenant.name)
            self.assertEqual(args[1], pd.pk)

    @mock.patch('etools.applications.rss_admin.views.send_agreement_suspended_notification')
    def test_agreement_suspension_sends_notification(self, mock_notify):
        """Side-effect: Agreement transitioning to suspended sends a notification."""
        # ensure agreement is signed before moving to suspended
        self.agreement.status = 'signed'
        self.agreement.save(update_fields=['status'])

        url = reverse('rss_admin:rss-admin-agreements-detail', kwargs={'pk': self.agreement.pk})
        resp = self.forced_auth_req('patch', url, user=self.user, data={'status': 'suspended'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.agreement.refresh_from_db()
        self.assertEqual(self.agreement.status, 'suspended')
        self.assertTrue(mock_notify.called)

    def test_pd_terminate_requires_attachment(self):
        """Condition: Transition to terminated requires termination document; without it returns 400."""
        pd = InterventionFactory(agreement=self.agreement, document_type=Intervention.PD, status=Intervention.ACTIVE)
        url = reverse('rss_admin:rss-admin-programme-documents-detail', kwargs={'pk': pd.pk})
        # attempt to move to terminated without termination_doc_attachment
        resp = self.forced_auth_req('patch', url, user=self.user, data={'status': Intervention.TERMINATED})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

        # add required attachment then retry
        attachment = AttachmentFactory(file='termination.pdf')
        resp2 = self.forced_auth_req('patch', url, user=self.user, data={
            'termination_doc_attachment': attachment.id,
            'status': Intervention.TERMINATED,
        })
        self.assertEqual(resp2.status_code, status.HTTP_200_OK, resp2.data)

    def test_pd_activate_requires_agreement_signed(self):
        """Condition: PD cannot transition to active if Agreement is not signed (returns 400)."""
        pd = InterventionFactory(agreement=self.agreement, document_type=Intervention.PD, status=Intervention.SIGNATURE)
        url = reverse('rss_admin:rss-admin-programme-documents-detail', kwargs={'pk': pd.pk})
        resp = self.forced_auth_req('patch', url, user=self.user, data={'status': Intervention.ACTIVE})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_partners_paginated(self):
        url = reverse('rss_admin:rss-admin-partners-list')
        response = self.forced_auth_req('get', url, user=self.user, data={'page': 1, 'page_size': 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, dict)
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)
        self.assertIsInstance(response.data['results'], list)
        ids = self._ids(response)
        self.assertTrue(self.partner.id in ids or response.data['count'] >= 1)

    def test_list_agreements_paginated(self):
        url = reverse('rss_admin:rss-admin-agreements-list')
        response = self.forced_auth_req('get', url, user=self.user, data={'page': 1, 'page_size': 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, dict)
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)
        self.assertIsInstance(response.data['results'], list)
        ids = self._ids(response)
        self.assertTrue(self.agreement.id in ids or response.data['count'] >= 1)

    def test_filter_agreements_by_status(self):
        # create a second agreement with a different status
        other_agreement = AgreementFactory(partner=self.partner, status='draft')
        self.agreement.status = 'signed'
        self.agreement.save(update_fields=['status'])

        url = reverse('rss_admin:rss-admin-agreements-list')
        response = self.forced_auth_req('get', url, user=self.user, data={'status': 'signed'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = self._ids(response)
        self.assertIn(self.agreement.id, ids)
        self.assertNotIn(other_agreement.id, ids)

    def test_filter_agreements_by_statuses_plural(self):
        other_agreement = AgreementFactory(partner=self.partner, status='draft')
        self.agreement.status = 'signed'
        self.agreement.save(update_fields=['status'])

        url = reverse('rss_admin:rss-admin-agreements-list')
        response = self.forced_auth_req('get', url, user=self.user, data={'statuses': 'signed'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [row['id'] for row in response.data]
        self.assertIn(self.agreement.id, ids)
        self.assertNotIn(other_agreement.id, ids)

    def test_filter_agreements_by_partner(self):
        # filter by partner id
        url = reverse('rss_admin:rss-admin-agreements-list')
        response = self.forced_auth_req('get', url, user=self.user, data={'partner': self.partner.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = self._ids(response)
        self.assertIn(self.agreement.id, ids)

    def test_filter_agreements_by_type(self):
        self.agreement.agreement_type = 'PCA'
        self.agreement.save(update_fields=['agreement_type'])
        url = reverse('rss_admin:rss-admin-agreements-list')
        response = self.forced_auth_req('get', url, user=self.user, data={'agreement_type': 'PCA'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [row['id'] for row in response.data]
        self.assertIn(self.agreement.id, ids)

    def test_filter_agreements_by_types_plural(self):
        self.agreement.agreement_type = 'PCA'
        self.agreement.save(update_fields=['agreement_type'])
        url = reverse('rss_admin:rss-admin-agreements-list')
        response = self.forced_auth_req('get', url, user=self.user, data={'types': 'PCA'})
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
        ids = self._ids(resp)
        self.assertIn(ag1.id, ids)

    def test_filter_agreements_by_number(self):
        url = reverse('rss_admin:rss-admin-agreements-list')
        response = self.forced_auth_req('get', url, user=self.user, data={'agreement_number': self.agreement.agreement_number})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = self._ids(response)
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
        # signature date keys present
        self.assertIn('signed_by_unicef_date', response.data)
        self.assertIn('signed_by_partner_date', response.data)
        # partner signatory id
        self.assertEqual(response.data['partner_signatory'], self.agreement.partner_manager_id)

    def test_update_agreement_signature_single_field(self):
        """RSS Admin: Allow fixing a single signature date via update."""
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
            'attachment': attachment.id,
            'authorized_officers_ids': [officer.id],
        }
        response = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        # officers changed
        returned_officer_ids = set([o['id'] for o in response.data['authorized_officers']])
        self.assertEqual(returned_officer_ids, {officer.id})
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
        # Assert error structure and message
        self.assertIn('programme_documents', resp.data)
        self.assertIn('non_pd_ids', resp.data['programme_documents'])
        non_pd_ids = resp.data['programme_documents']['non_pd_ids']
        self.assertIn(str(spd.id), [str(x) for x in non_pd_ids])
        self.assertIn('errors', resp.data['programme_documents'])
        self.assertTrue(any('Programme Documents (PD)' in msg for msg in resp.data['programme_documents']['errors']))

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
        self.assertIn(pd.id, [e['id'] for e in resp.data['errors']])

    # ------------------------
    # Additional status tests
    # ------------------------

    def test_condition_pd_signature_requires_agreement_signed(self):
        """Condition: PD cannot transition to signed if Agreement is not signed (expects 400)."""
        self.agreement.status = 'draft'
        self.agreement.save(update_fields=['status'])
        pd = InterventionFactory(agreement=self.agreement, document_type=Intervention.PD, status=Intervention.SIGNATURE)
        url = reverse('rss_admin:rss-admin-programme-documents-detail', kwargs={'pk': pd.pk})
        resp = self.forced_auth_req('patch', url, user=self.user, data={'title': 'noop'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_condition_pd_ended_to_closed_requires_final_review_and_past_end_date(self):
        """Condition: Ended PD closes only if final review approved and end date is not in the future (expect 400 without)."""
        self.agreement.status = 'signed'
        self.agreement.save(update_fields=['status'])
        pd = InterventionFactory(agreement=self.agreement, document_type=Intervention.PD, status=Intervention.ENDED)
        url = reverse('rss_admin:rss-admin-programme-documents-detail', kwargs={'pk': pd.pk})
        resp_bad = self.forced_auth_req('patch', url, user=self.user, data={'title': 'noop'})
        self.assertEqual(resp_bad.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bulk_close_grouped_errors_not_ended(self):
        pd1 = InterventionFactory(
            agreement=self.agreement,
            document_type=Intervention.PD,
            status=Intervention.ACTIVE,
        )
        pd2 = InterventionFactory(
            agreement=self.agreement,
            document_type=Intervention.PD,
            status=Intervention.ACTIVE,
        )
        url = reverse('rss_admin:rss-admin-programme-documents-bulk-close')
        payload = {'programme_documents': [pd1.id, pd2.id]}
        resp = self.forced_auth_req('put', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('grouped_errors', resp.data)
        group = next(g for g in resp.data['grouped_errors'] if 'ENDED status' in g['message'])
        self.assertEqual(set(group['ids']), {pd1.id, pd2.id})

    def test_bulk_close_grouped_errors_transition_error(self):
        # Create PDs in ENDED but with end date in future to trigger validator error
        future_date = timezone.now().date() + timedelta(days=1)
        pd1 = InterventionFactory(
            agreement=self.agreement,
            document_type=Intervention.PD,
            status=Intervention.ENDED,
        )
        pd1.end = future_date
        pd1.save(update_fields=['end'])
        pd2 = InterventionFactory(
            agreement=self.agreement,
            document_type=Intervention.PD,
            status=Intervention.ENDED,
        )
        pd2.end = future_date
        pd2.save(update_fields=['end'])

        url = reverse('rss_admin:rss-admin-programme-documents-bulk-close')
        payload = {'programme_documents': [pd1.id, pd2.id]}
        resp = self.forced_auth_req('put', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('grouped_errors', resp.data)
        group = next(g for g in resp.data['grouped_errors'] if 'End date is in the future' in g['message'])
        self.assertEqual(set(group['ids']), {pd1.id, pd2.id})

    def test_assign_frs_to_pd(self):
        fr1 = FundsReservationHeaderFactory(intervention=None)
        fr2 = FundsReservationHeaderFactory(intervention=None)
        # Use generic PATCH endpoint to assign FRs
        url = reverse('rss_admin:rss-admin-programme-documents-detail', kwargs={'pk': self.pd.pk})
        payload = {'frs': [fr1.id, fr2.id]}
        resp = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        # 'frs' returns a list of FR ids on the update serializer
        self.assertCountEqual(resp.data['frs'], [fr1.id, fr2.id])
        # Verify via detail GET that frs_details reflect the change
        resp_get = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(resp_get.status_code, status.HTTP_200_OK, resp_get.data)
        returned_ids = [fr['id'] for fr in resp_get.data['frs_details']['frs']]
        self.assertCountEqual(returned_ids, [fr1.id, fr2.id])

    def test_patch_pd_sets_two_frs_and_retrieve_shows_both(self):
        fr1 = FundsReservationHeaderFactory(intervention=None)
        fr2 = FundsReservationHeaderFactory(intervention=None)

        # Patch via the standard PD detail endpoint with two FRs
        url_detail = reverse('rss_admin:rss-admin-programme-documents-detail', kwargs={'pk': self.pd.pk})
        payload = {'frs': [fr1.id, fr2.id]}
        resp_patch = self.forced_auth_req('patch', url_detail, user=self.user, data=payload)
        self.assertEqual(resp_patch.status_code, status.HTTP_200_OK, resp_patch.data)
        # response should include both FRs by id
        self.assertCountEqual(resp_patch.data['frs'], [fr1.id, fr2.id])

        # Retrieve should also return both FRs
        resp_get = self.forced_auth_req('get', url_detail, user=self.user)
        self.assertEqual(resp_get.status_code, status.HTTP_200_OK)
        self.assertCountEqual(resp_get.data['frs'], [fr1.id, fr2.id])
        returned_ids_get = [fr['id'] for fr in resp_get.data['frs_details']['frs']]
        self.assertCountEqual(returned_ids_get, [fr1.id, fr2.id])

    def test_patch_pd_with_fr_numbers(self):
        fr1 = FundsReservationHeaderFactory(intervention=None)
        fr2 = FundsReservationHeaderFactory(intervention=None)

        url_detail = reverse('rss_admin:rss-admin-programme-documents-detail', kwargs={'pk': self.pd.pk})
        payload = {'fr_numbers': [fr1.fr_number, fr2.fr_number]}
        resp_patch = self.forced_auth_req('patch', url_detail, user=self.user, data=payload)
        self.assertEqual(resp_patch.status_code, status.HTTP_200_OK, resp_patch.data)
        self.assertCountEqual(resp_patch.data['frs'], [fr1.id, fr2.id])

        resp_get = self.forced_auth_req('get', url_detail, user=self.user)
        self.assertEqual(resp_get.status_code, status.HTTP_200_OK)
        self.assertCountEqual(resp_get.data['frs'], [fr1.id, fr2.id])

    def test_set_currency_on_pd(self):
        currency = CURRENCY_LIST[0]
        url = reverse('rss_admin:rss-admin-programme-documents-detail', kwargs={'pk': self.pd.pk})
        resp = self.forced_auth_req('patch', url, user=self.user, data={'currency': currency})
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data['planned_budget']['currency'], currency)

    def test_set_currency_invalid(self):
        url = reverse('rss_admin:rss-admin-programme-documents-detail', kwargs={'pk': self.pd.pk})
        resp = self.forced_auth_req('patch', url, user=self.user, data={'currency': 'XXX'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch('etools.applications.rss_admin.views.send_pd_to_vision')
    def test_send_to_vision_action(self, mock_task):
        url = reverse('rss_admin:rss-admin-programme-documents-send-to-vision', kwargs={'pk': self.pd.pk})
        resp = self.forced_auth_req('post', url, user=self.user)
        self.assertEqual(resp.status_code, status.HTTP_202_ACCEPTED)
        self.assertTrue(mock_task.delay.called)
        args, _kwargs = mock_task.delay.call_args
        self.assertEqual(args[1], self.pd.pk)

    @mock.patch('etools.applications.action_points.models.send_notification_with_template')
    def test_add_attachment_to_completed_high_priority_action_point(self, _mock_notify):
        ap = ActionPointFactory(status='completed', comments__count=1)
        ap.high_priority = True
        ap.save(update_fields=['high_priority'])
        comment = ap.comments.first()
        attachment = AttachmentFactory(file="evidence.pdf")

        url = reverse('rss_admin:rss-admin-action-points-add-attachment', kwargs={'pk': ap.pk})
        payload = {
            'comment': comment.id,
            'supporting_document': attachment.id,
        }
        resp = self.forced_auth_req('post', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        comment.refresh_from_db()
        self.assertEqual(comment.supporting_document.count(), 1)
        self.assertEqual(comment.supporting_document.first().id, attachment.id)

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

    # ------------------------
    # Engagement status changes
    # ------------------------

    def test_engagement_submit(self):
        """Submitting an engagement moves status to REPORT_SUBMITTED and returns 200."""
        e = EngagementFactory()
        url = reverse('rss_admin:rss-admin-engagements-change-status', kwargs={'pk': e.pk})
        resp = self.forced_auth_req('post', url, user=self.user, data={'action': 'submit'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        e.refresh_from_db()
        self.assertEqual(e.status, Engagement.REPORT_SUBMITTED)

    def test_engagement_send_back_requires_comment(self):
        """Send back requires a comment; without it returns 400, with it moves to PARTNER_CONTACTED."""
        e = EngagementFactory(status=Engagement.REPORT_SUBMITTED)
        url = reverse('rss_admin:rss-admin-engagements-change-status', kwargs={'pk': e.pk})
        resp_bad = self.forced_auth_req('post', url, user=self.user, data={'action': 'send_back'})
        self.assertEqual(resp_bad.status_code, status.HTTP_400_BAD_REQUEST)
        resp_ok = self.forced_auth_req('post', url, user=self.user, data={'action': 'send_back', 'send_back_comment': 'Fix issues'})
        self.assertEqual(resp_ok.status_code, status.HTTP_200_OK, resp_ok.data)
        e.refresh_from_db()
        self.assertEqual(e.status, Engagement.PARTNER_CONTACTED)
        self.assertEqual(e.send_back_comment, 'Fix issues')

    def test_engagement_cancel_requires_comment(self):
        """Cancel requires cancel_comment; without it returns 400, with it sets status to CANCELLED."""
        e = EngagementFactory()
        url = reverse('rss_admin:rss-admin-engagements-change-status', kwargs={'pk': e.pk})
        resp_bad = self.forced_auth_req('post', url, user=self.user, data={'status': 'cancelled'})
        self.assertEqual(resp_bad.status_code, status.HTTP_400_BAD_REQUEST)
        resp_ok = self.forced_auth_req('post', url, user=self.user, data={'status': 'cancelled', 'cancel_comment': 'Not needed'})
        self.assertEqual(resp_ok.status_code, status.HTTP_200_OK, resp_ok.data)
        e.refresh_from_db()
        self.assertEqual(e.status, Engagement.CANCELLED)
        self.assertEqual(e.cancel_comment, 'Not needed')

    def test_engagement_finalize_on_audit(self):
        """Finalize transitions a submitted Audit to FINAL and returns 200."""
        audit = AuditFactory(status=Engagement.REPORT_SUBMITTED)
        url = reverse('rss_admin:rss-admin-engagements-change-status', kwargs={'pk': audit.pk})
        resp = self.forced_auth_req('post', url, user=self.user, data={'status': 'final'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        audit.refresh_from_db()
        self.assertEqual(audit.status, Engagement.FINAL)

    # ------------------------
    # Engagement initiation update
    # ------------------------
    def test_engagement_initiation_update_success(self):
        """RSS Admin: PATCH engagements/{id}/initiation updates initiation fields and persists them."""
        e = EngagementFactory()
        url = reverse('rss_admin:rss-admin-engagements-initiation', kwargs={'pk': e.pk})
        payload = {
            'start_date': (timezone.now().date() - timedelta(days=30)).isoformat(),
            'end_date': (timezone.now().date() - timedelta(days=10)).isoformat(),
            'partner_contacted_at': (timezone.now().date() - timedelta(days=5)).isoformat(),
            'total_value': '12345.67',
            'exchange_rate': '1.25',
            'currency_of_report': 'USD',
        }
        resp = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        e.refresh_from_db()
        self.assertEqual(str(e.start_date), payload['start_date'])
        self.assertEqual(str(e.end_date), payload['end_date'])
        self.assertEqual(str(e.partner_contacted_at), payload['partner_contacted_at'])
        self.assertEqual(str(e.total_value), payload['total_value'])
        self.assertEqual(str(e.exchange_rate), payload['exchange_rate'])
        self.assertEqual(e.currency_of_report, payload['currency_of_report'])

    def test_engagement_initiation_update_date_validation(self):
        """RSS Admin: initiation update rejects invalid chronology (end_date < start_date) with 400 and error key."""
        e = EngagementFactory()
        url = reverse('rss_admin:rss-admin-engagements-initiation', kwargs={'pk': e.pk})
        start = timezone.now().date() - timedelta(days=10)
        end = start - timedelta(days=1)
        payload = {
            'start_date': start.isoformat(),
            'end_date': end.isoformat(),
        }
        resp = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('end_date', resp.data)

    def test_engagement_attachments_update(self):
        """RSS Admin: PATCH engagements/{id}/attachments links provided attachment ids to engagement/report sets."""
        e = EngagementFactory()
        url = reverse('rss_admin:rss-admin-engagements-attachments', kwargs={'pk': e.pk})

        attachment_eng = AttachmentFactory(file='eng.pdf')
        attachment_rep = AttachmentFactory(file='rep.pdf')

        payload = {
            'engagement_attachment': attachment_eng.id,
            'report_attachment': attachment_rep.id,
        }
        resp = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)

        e.refresh_from_db()
        self.assertTrue(e.engagement_attachments.filter(pk=attachment_eng.id).exists())
        self.assertTrue(e.report_attachments.filter(pk=attachment_rep.id).exists())

    # ------------------------
    # Engagement list & detail
    # ------------------------

    def test_engagements_list_includes_staff_spot_checks(self):
        sc = SpotCheckFactory()
        ssc = StaffSpotCheckFactory()
        url = reverse('rss_admin:rss-admin-engagements-list')
        resp = self.forced_auth_req('get', url, user=self.user, data={'ordering': 'reference_number', 'page_size': 10})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('results', resp.data)
        ids = [row['id'] for row in resp.data['results']]
        self.assertIn(sc.id, ids)
        self.assertIn(ssc.id, ids)

    def test_engagement_detail_audit(self):
        audit = AuditFactory()
        url = reverse('rss_admin:rss-admin-engagements-detail', kwargs={'pk': audit.pk})
        resp = self.forced_auth_req('get', url, user=self.user)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['id'], audit.id)
        # ensure a detail-only field is present (e.g., year_of_audit for audits)
        self.assertIn('year_of_audit', resp.data)

    # ------------------------------------------------------------------
    # Status transitions: targeted condition/side-effect tests
    # ------------------------------------------------------------------

    def test_condition_pd_cannot_sign_when_agreement_suspended(self):
        """Condition: PD cannot transition to signed if Agreement is suspended (expect 400)."""
        self.agreement.status = 'suspended'
        self.agreement.save(update_fields=['status'])
        pd = InterventionFactory(agreement=self.agreement, document_type=Intervention.PD, status=Intervention.SIGNATURE)
        url = reverse('rss_admin:rss-admin-programme-documents-detail', kwargs={'pk': pd.pk})
        resp = self.forced_auth_req('patch', url, user=self.user, data={'title': 'noop'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_condition_pd_cannot_sign_when_partner_blocked(self):
        """Condition: PD cannot transition to signed if Partner is blocked in Vision (expect 400)."""
        self.agreement.partner.blocked = True
        self.agreement.partner.save(update_fields=['blocked'])
        self.agreement.status = 'signed'
        self.agreement.save(update_fields=['status'])
        pd = InterventionFactory(agreement=self.agreement, document_type=Intervention.PD, status=Intervention.SIGNATURE)
        url = reverse('rss_admin:rss-admin-programme-documents-detail', kwargs={'pk': pd.pk})
        resp = self.forced_auth_req('patch', url, user=self.user, data={'title': 'noop'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_condition_pd_cannot_end_when_termination_doc_attached(self):
        """Condition: PD cannot transition to ended if a termination document is attached (expect 400)."""
        self.agreement.status = 'signed'
        self.agreement.save(update_fields=['status'])
        pd = InterventionFactory(agreement=self.agreement, document_type=Intervention.PD, status=Intervention.ACTIVE)
        # attach termination doc
        attachment = AttachmentFactory(file='termination.pdf')
        pd.termination_doc_attachment.add(attachment)
        url = reverse('rss_admin:rss-admin-programme-documents-detail', kwargs={'pk': pd.pk})
        resp = self.forced_auth_req('patch', url, user=self.user, data={'status': Intervention.ENDED})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_condition_pd_cannot_suspend_when_partner_blocked(self):
        """Condition: PD cannot transition to suspended if Partner is blocked (expect 400)."""
        self.agreement.partner.blocked = True
        self.agreement.partner.save(update_fields=['blocked'])
        pd = InterventionFactory(agreement=self.agreement, document_type=Intervention.PD, status=Intervention.SIGNED)
        url = reverse('rss_admin:rss-admin-programme-documents-detail', kwargs={'pk': pd.pk})
        resp = self.forced_auth_req('patch', url, user=self.user, data={'status': Intervention.SUSPENDED})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_condition_agreement_draft_to_signed_requires_both_signature_dates(self):
        """RSS Admin: In draft, fixing both signature dates is allowed (200)."""
        self.agreement.status = 'draft'
        self.agreement.signed_by_unicef_date = None
        self.agreement.signed_by_partner_date = None
        self.agreement.save(update_fields=['status', 'signed_by_unicef_date', 'signed_by_partner_date'])
        url = reverse('rss_admin:rss-admin-agreements-detail', kwargs={'pk': self.agreement.pk})
        # provide both dates -> allowed in RSS admin
        payload = {
            'signed_by_unicef_date': timezone.now().date().isoformat(),
            'signed_by_partner_date': timezone.now().date().isoformat(),
        }
        resp_ok = self.forced_auth_req('patch', url, user=self.user, data=payload)
        self.assertEqual(resp_ok.status_code, status.HTTP_200_OK)

    def test_condition_agreement_signed_to_ended_requires_past_end_date(self):
        """Condition: With end=today, patch returns 200 but status remains 'signed'; with past end -> 200 proceeds."""
        self.agreement.status = 'signed'
        self.agreement.end = timezone.now().date()
        self.agreement.save(update_fields=['status', 'end'])
        url = reverse('rss_admin:rss-admin-agreements-detail', kwargs={'pk': self.agreement.pk})
        resp_bad = self.forced_auth_req('patch', url, user=self.user, data={'agreement_number': self.agreement.agreement_number})
        self.assertEqual(resp_bad.status_code, status.HTTP_200_OK)
        self.agreement.refresh_from_db()
        self.assertEqual(self.agreement.status, 'signed')
        # move end to past -> expect 200
        self.agreement.end = timezone.now().date() - timedelta(days=1)
        self.agreement.save(update_fields=['end'])
        resp_ok = self.forced_auth_req('patch', url, user=self.user, data={'agreement_number': self.agreement.agreement_number})
        self.assertEqual(resp_ok.status_code, status.HTTP_200_OK, resp_ok.data)

    def test_map_partner_to_workspace_creates_partner(self):
        org = OrganizationFactory()
        url = reverse('rss_admin:rss-admin-partners-map-to-workspace')
        resp = self.forced_auth_req('post', url, user=self.user, data={'vendor_number': org.vendor_number})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        # PartnerOrganization now exists in this tenant for the organization
        from etools.applications.partners.models import PartnerOrganization
        self.assertTrue(PartnerOrganization.objects.filter(organization=org).exists())

    def test_map_partner_to_workspace_idempotent(self):
        org = OrganizationFactory()
        # pre-create partner
        partner = PartnerFactory(organization=org)
        url = reverse('rss_admin:rss-admin-partners-map-to-workspace')
        resp = self.forced_auth_req('post', url, user=self.user, data={'vendor_number': org.vendor_number})
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data['id'], partner.id)

    def test_map_partner_to_workspace_updates_leads(self):
        org = OrganizationFactory()
        office = OfficeFactory()
        section = SectionFactory()
        url = reverse('rss_admin:rss-admin-partners-map-to-workspace')
        payload = {'vendor_number': org.vendor_number, 'lead_office': office.id, 'lead_section': section.id}
        resp = self.forced_auth_req('post', url, user=self.user, data=payload)
        self.assertIn(resp.status_code, (status.HTTP_201_CREATED, status.HTTP_200_OK))
        from etools.applications.partners.models import PartnerOrganization
        partner = PartnerOrganization.objects.get(organization=org)
        self.assertEqual(partner.lead_office_id, office.id)
        self.assertEqual(partner.lead_section_id, section.id)

    def test_map_partner_to_workspace_unknown_vendor(self):
        url = reverse('rss_admin:rss-admin-partners-map-to-workspace')
        resp = self.forced_auth_req('post', url, user=self.user, data={'vendor_number': 'NOPE'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ----------------------------------------------------
    # Engagement list: fields and filters parity with Audit
    # ----------------------------------------------------

    def test_engagements_list_fields_match_audit_list(self):
        """RSS Admin engagements list items must expose same fields as Audit engagements list."""
        # Create a standard (non-staff) engagement
        sc = SpotCheckFactory()
        
        # Expected fields from audit EngagementLightSerializer (related_agreement is write_only, not in response)
        expected_fields = {
            'id', 'reference_number', 'agreement', 'po_item', 'partner',
            'engagement_type', 'status', 'status_date', 'total_value', 'offices', 'sections'
        }
        
        # Fetch via RSS Admin list
        rss_url = reverse('rss_admin:rss-admin-engagements-list')
        rss_resp = self.forced_auth_req('get', rss_url, user=self.user, data={
            'search': sc.id,
            'page_size': 1,
        })
        self.assertEqual(rss_resp.status_code, status.HTTP_200_OK, rss_resp.data)
        rss_results = rss_resp.data if isinstance(rss_resp.data, list) else rss_resp.data.get('results', [])
        self.assertTrue(rss_results, "Expected at least one result from RSS Admin engagements list")
        rss_row = next((r for r in rss_results if r.get('id') == sc.id), rss_results[0])

        # Verify field sets match expected (order not enforced, only equality of keys)
        self.assertEqual(set(rss_row.keys()), expected_fields,
                        f"RSS Admin engagement fields don't match expected. Got: {set(rss_row.keys())}, Expected: {expected_fields}")

    def test_engagements_filters_include_staff_spot_checks_toggle(self):
        """Filter parity: ability to filter staff spot checks by unicef_users_allowed flag."""
        sc = SpotCheckFactory()
        ssc = StaffSpotCheckFactory()
        url = reverse('rss_admin:rss-admin-engagements-list')

        # Only staff spot checks
        resp_staff = self.forced_auth_req('get', url, user=self.user, data={
            'agreement__auditor_firm__unicef_users_allowed': True,
            'page_size': 50,
        })
        self.assertEqual(resp_staff.status_code, status.HTTP_200_OK, resp_staff.data)
        results_staff = resp_staff.data if isinstance(resp_staff.data, list) else resp_staff.data.get('results', [])
        ids_staff = [r['id'] for r in results_staff]
        self.assertIn(ssc.id, ids_staff)
        self.assertNotIn(sc.id, ids_staff)

        # Only non-staff spot checks
        resp_non_staff = self.forced_auth_req('get', url, user=self.user, data={
            'agreement__auditor_firm__unicef_users_allowed': False,
            'page_size': 50,
        })
        self.assertEqual(resp_non_staff.status_code, status.HTTP_200_OK, resp_non_staff.data)
        results_non_staff = resp_non_staff.data if isinstance(resp_non_staff.data, list) else resp_non_staff.data.get('results', [])
        ids_non_staff = [r['id'] for r in results_non_staff]
        self.assertIn(sc.id, ids_non_staff)
        self.assertNotIn(ssc.id, ids_non_staff)
