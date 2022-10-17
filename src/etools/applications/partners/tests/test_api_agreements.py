import datetime
import json

from django.test import SimpleTestCase
from django.urls import reverse

import mock
from rest_framework import status
from unicef_attachments.models import Attachment
from unicef_snapshot.models import Activity

from etools.applications.attachments.tests.factories import AttachmentFactory, AttachmentFileTypeFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.core.tests.mixins import URLAssertionMixin
from etools.applications.organizations.models import OrganizationType
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.models import Agreement, AgreementAmendment, Intervention
from etools.applications.partners.permissions import PARTNERSHIP_MANAGER_GROUP, UNICEF_USER
from etools.applications.partners.tests.factories import AgreementFactory, InterventionFactory, PartnerFactory
from etools.applications.reports.tests.factories import CountryProgrammeFactory
from etools.applications.users.tests.factories import UserFactory


class URLsTestCase(URLAssertionMixin, SimpleTestCase):
    """Simple test case to verify URL reversal"""

    def test_urls(self):
        """Verify URL pattern names generate the URLs we expect them to."""
        names_and_paths = (
            ('agreement-list', '', {}),
            ('agreement-detail', '1/', {'pk': 1}),
            ('pca_pdf', '1/generate_doc/', {'agr': 1}),
            ('agreement-amendment-del', 'amendments/1/', {'pk': 1}),
            ('agreement-amendment-list', 'amendments/', {}),
        )
        self.assertReversal(names_and_paths, 'partners_api:', '/api/v2/agreements/')
        self.assertIntParamRegexes(names_and_paths, 'partners_api:')


class TestAgreementsAPI(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.partnership_manager_user = UserFactory(
            is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]
        )
        cls.partner1 = PartnerFactory(
            organization=OrganizationFactory(organization_type=OrganizationType.CIVIL_SOCIETY_ORGANIZATION))
        cls.country_programme = CountryProgrammeFactory()
        cls.agreement1 = AgreementFactory(partner=cls.partner1, signed_by_unicef_date=datetime.date.today())
        cls.intervention = InterventionFactory(agreement=cls.agreement1)
        cls.intervention_2 = InterventionFactory(agreement=cls.agreement1, document_type=Intervention.PD)
        cls.amendment = AgreementAmendment.objects.create(agreement=cls.agreement1,
                                                          types=[AgreementAmendment.IP_NAME,
                                                                 AgreementAmendment.CLAUSE],
                                                          number="001",
                                                          signed_amendment="application/pdf",
                                                          signed_date=datetime.date.today())
        cls.file_type_agreement = AttachmentFileTypeFactory(
            code="partners_agreement",
        )
        cls.file_type_agreement_amendment = AttachmentFileTypeFactory(
            code="partners_agreement_amendment",
        )

    def run_request_list_ep(self, data={}, user=None, method='post'):
        response = self.forced_auth_req(
            method,
            reverse('partners_api:agreement-list'),
            user=user or self.partnership_manager_user,
            data=data
        )
        return response.status_code, json.loads(response.rendered_content)

    def run_request(self, agreement_id, data=None, method='get', user=None):
        response = self.forced_auth_req(
            method,
            reverse('partners_api:agreement-detail', kwargs={'pk': agreement_id}),
            user=user or self.partnership_manager_user,
            data=data or {}
        )
        return response.status_code, json.loads(response.rendered_content)

    def test_agreement_detail_attachment_empty(self):
        status_code, response = self.run_request(self.agreement1.pk)

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertIsNone(response["attachment"])

    def test_agreement_detail_attachment(self):
        attachment = AttachmentFactory(
            content_object=self.agreement1,
            file_type=self.file_type_agreement,
            code=self.file_type_agreement.code,
            file="test_file.pdf"
        )
        status_code, response = self.run_request(self.agreement1.pk)

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertTrue(response["attachment"].endswith(attachment.file.url))

    def test_add_new_PCA(self):
        self.assertFalse(Activity.objects.exists())
        data = {
            "agreement_type": Agreement.PCA,
            "partner": self.partner1.id,
            "country_programme": self.country_programme.id,
            "reference_number_year": datetime.date.today().year,
        }
        status_code, response = self.run_request_list_ep(data)

        self.assertEqual(status_code, status.HTTP_201_CREATED)
        self.assertEqual(response['agreement_type'], Agreement.PCA)
        self.assertEqual(
            Activity.objects.filter(action=Activity.CREATE).count(),
            1
        )

    def test_add_new_PCA_with_attachment(self):
        attachment = AttachmentFactory(
            file="test_file.pdf",
            file_type=None,
            code="",
        )
        self.assertIsNone(attachment.file_type)
        self.assertIsNone(attachment.content_object)
        self.assertFalse(attachment.code)
        self.assertFalse(Activity.objects.exists())
        data = {
            "agreement_type": Agreement.PCA,
            "partner": self.partner1.id,
            "country_programme": self.country_programme.id,
            "attachment": attachment.pk,
            "reference_number_year": datetime.date.today().year,
        }
        status_code, response = self.run_request_list_ep(data)
        self.assertEqual(status_code, status.HTTP_201_CREATED)
        self.assertEqual(response['agreement_type'], Agreement.PCA)
        self.assertEqual(
            Activity.objects.filter(action=Activity.CREATE).count(),
            1
        )
        attachment_updated = Attachment.objects.get(pk=attachment.pk)
        self.assertEqual(
            attachment_updated.file_type.code,
            self.file_type_agreement.code
        )
        self.assertEqual(attachment_updated.object_id, response["id"])
        self.assertEqual(
            attachment_updated.code,
            self.file_type_agreement.code
        )

    def test_fail_add_new_PCA_without_agreement_type(self):
        self.assertFalse(Activity.objects.exists())
        data = {
            "partner": self.partner1.id,
            "country_programme": self.country_programme.id,
        }
        status_code, response = self.run_request_list_ep(data)

        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response['agreement_type'], ['This field is required.'])
        self.assertFalse(Activity.objects.exists())

    def test_fail_add_new_PCA_without_country_programme(self):
        self.assertFalse(Activity.objects.exists())
        data = {
            "agreement_type": Agreement.PCA,
            "partner": self.partner1.id,
            "reference_number_year": datetime.date.today().year,
        }
        status_code, response = self.run_request_list_ep(data)

        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response['country_programme'], ['Country Programme is required for PCAs!'])
        self.assertFalse(Activity.objects.exists())

    def test_add_new_SSFA_without_country_programme(self):
        self.assertFalse(Activity.objects.exists())
        data = {
            "agreement_type": Agreement.SSFA,
            "partner": self.partner1.id,
            "reference_number_year": datetime.date.today().year,
        }
        status_code, response = self.run_request_list_ep(data)

        self.assertEqual(status_code, status.HTTP_201_CREATED)
        self.assertEqual(response['agreement_type'], Agreement.SSFA)
        self.assertEqual(
            Activity.objects.filter(action=Activity.CREATE).count(),
            1
        )

    def test_add_new_SSFA_with_country_programme_null(self):
        self.assertFalse(Activity.objects.exists())
        data = {
            "agreement_type": Agreement.SSFA,
            "partner": self.partner1.id,
            "country_programme": 'null',
            "reference_number_year": datetime.date.today().year,
        }
        status_code, response = self.run_request_list_ep(data)

        self.assertEqual(status_code, status.HTTP_201_CREATED)
        self.assertEqual(response['agreement_type'], Agreement.SSFA)
        self.assertEqual(
            Activity.objects.filter(action=Activity.CREATE).count(),
            1
        )

    def test_fail_patch_PCA_without_country_programme(self):
        # create new agreement
        self.assertFalse(Activity.objects.exists())
        data = {
            "agreement_type": Agreement.SSFA,
            "partner": self.partner1.id,
            "reference_number_year": datetime.date.today().year,
        }
        status_code, response = self.run_request_list_ep(data)
        self.assertTrue(Activity.objects.exists())
        agreement_id = response['id']

        # change agreement type to a PCA
        data = {
            "agreement_type": Agreement.PCA
        }
        status_code, response = self.run_request(agreement_id, data, method='patch')
        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response['country_programme'], ['Country Programme is required for PCAs!'])
        self.assertTrue(Activity.objects.exists())

    def test_fail_patch_PCA_without_PartnershipManagerPermission(self):
        # create new agreement
        # change agreement type to a PCA
        self.assertFalse(Activity.objects.exists())
        data = {
            "agreement_type": Agreement.PCA
        }
        status_code, response = self.run_request(self.agreement1.id, data, method='patch', user=self.unicef_staff)
        self.assertEqual(status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response['detail'], 'Accessing this item is not allowed.')
        self.assertFalse(Activity.objects.exists())

    def test_fail_add_PCA_without_PartnershipManagerPermission(self):
        self.assertFalse(Activity.objects.exists())
        data = {
            "agreement_type": Agreement.PCA,
            "partner": self.partner1.id,
            "country_programme": self.country_programme.id,
            "reference_number_year": datetime.date.today().year
        }
        status_code, response = self.run_request_list_ep(data, user=self.unicef_staff)
        self.assertEqual(status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response['detail'], 'Accessing this item is not allowed.')
        self.assertFalse(Activity.objects.exists())

    def test_list_agreements(self):
        with self.assertNumQueries(2):
            status_code, response = self.run_request_list_ep(user=self.unicef_staff, method='get')

        self.assertEqual(status_code, status.HTTP_200_OK)

    def test_filter_agreements_special_condition(self):
        assert not self.agreement1.special_conditions_pca
        with self.assertNumQueries(1):
            status_code, response = self.run_request_list_ep(
                user=self.unicef_staff,
                method='get',
                data={"special_conditions_pca": True}
            )

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(response), 0)

        with self.assertNumQueries(2):
            status_code, response = self.run_request_list_ep(
                user=self.unicef_staff,
                method='get',
                data={"special_conditions_pca": False}
            )

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertEqual(len(response), 1)

    def test_add_new_PCA_with_amendment(self):
        attachment = AttachmentFactory(
            file="test_file.pdf",
            file_type=None,
            code="",
        )
        attachment_amendment = AttachmentFactory(
            file="test_file_amendment.pdf",
            file_type=None,
            code="",
        )
        self.assertIsNone(attachment.file_type)
        self.assertIsNone(attachment.content_object)
        self.assertFalse(attachment.code)
        self.assertIsNone(attachment_amendment.file_type)
        self.assertIsNone(attachment_amendment.content_object)
        self.assertFalse(attachment_amendment.code)
        self.assertFalse(Activity.objects.exists())
        data = {
            "agreement_type": Agreement.PCA,
            "reference_number_year": datetime.date.today().year,
            "partner": self.partner1.id,
            "country_programme": self.country_programme.id,
            "attachment": attachment.pk,
            "amendments": [{
                "types": [AgreementAmendment.CLAUSE, ],
                "signed_date": datetime.date.today().strftime("%Y-%m-%d"),
                "signed_amendment_attachment": attachment_amendment.pk,
            }]
        }
        status_code, response = self.run_request_list_ep(data)
        self.assertEqual(status_code, status.HTTP_201_CREATED)
        self.assertEqual(response['agreement_type'], Agreement.PCA)
        self.assertEqual(
            Activity.objects.filter(action=Activity.CREATE).count(),
            1
        )
        attachment_updated = Attachment.objects.get(pk=attachment.pk)
        self.assertEqual(
            attachment_updated.file_type.code,
            self.file_type_agreement.code
        )
        self.assertEqual(attachment_updated.object_id, response["id"])
        self.assertEqual(
            attachment_updated.code,
            self.file_type_agreement.code
        )
        attachment_amendment_updated = Attachment.objects.get(
            pk=attachment_amendment.pk
        )
        self.assertEqual(
            attachment_amendment_updated.file_type.code,
            self.file_type_agreement_amendment.code
        )
        self.assertEqual(
            attachment_amendment_updated.object_id,
            response["amendments"][0]["id"]
        )
        self.assertEqual(
            attachment_amendment_updated.code,
            self.file_type_agreement_amendment.code
        )

    def test_patch_agreement_with_attachment_as_url(self):
        agreement = AgreementFactory(
            partner=self.partner1,
            status=Agreement.DRAFT
        )
        AttachmentFactory(
            content_object=agreement,
            file_type=self.file_type_agreement,
            code=self.file_type_agreement.code,
            file="test_file.pdf",
        )
        status_code, response = self.run_request(agreement.pk)
        self.assertEqual(status_code, status.HTTP_200_OK)

        data = {
            "attachment": response["attachment"]
        }
        status_code, response = self.run_request(
            agreement.pk,
            data,
            method="patch",
        )

        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response["attachment"],
            ["Attachment expects an integer"]
        )

    def test_patch_agreement_with_attachment_as_pk(self):
        agreement = AgreementFactory(
            partner=self.partner1,
            status=Agreement.DRAFT
        )
        attachment = AttachmentFactory(
            file="test_file.pdf",
            file_type=None,
            code="",
        )
        self.assertIsNone(attachment.content_object)
        self.assertIsNone(attachment.file_type)
        self.assertEqual(attachment.code, "")

        data = {
            "attachment": attachment.pk
        }
        status_code, response = self.run_request(
            agreement.pk,
            data,
            method="patch",
        )

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertTrue(response["attachment"].endswith(attachment.file.url))
        attachment_update = Attachment.objects.get(pk=attachment.pk)
        self.assertEqual(attachment_update.content_object, agreement)
        self.assertEqual(attachment_update.file_type, self.file_type_agreement)
        self.assertEqual(attachment_update.code, self.file_type_agreement.code)

    def test_patch_agreement_without_attachment(self):
        agreement = AgreementFactory(
            partner=self.partner1,
            status=Agreement.DRAFT
        )
        attachment = AttachmentFactory(
            file="test_file.pdf",
            file_type=None,
            code="",
        )
        self.assertIsNone(attachment.content_object)
        self.assertIsNone(attachment.file_type)
        self.assertEqual(attachment.code, "")

        data = {
            "agreement_type": Agreement.PCA
        }
        status_code, response = self.run_request(
            agreement.pk,
            data,
            method="patch",
        )

        self.assertEqual(status_code, status.HTTP_200_OK)

    def test_patch_agreement_replace_attachment(self):
        agreement = AgreementFactory(
            partner=self.partner1,
            status=Agreement.DRAFT
        )
        attachment_current = AttachmentFactory(
            content_object=agreement,
            file_type=self.file_type_agreement,
            code=self.file_type_agreement.code,
            file="old_file.pdf",
        )
        attachment_new = AttachmentFactory(
            file="new_file.pdf",
            file_type=None,
            code="",
        )

        status_code, response = self.run_request(agreement.pk)
        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertTrue(
            response["attachment"].endswith(attachment_current.file.url)
        )

        data = {
            "attachment": attachment_new.pk
        }
        status_code, response = self.run_request(
            agreement.pk,
            data,
            method="patch",
        )

        self.assertEqual(status_code, status.HTTP_200_OK)
        self.assertTrue(
            response["attachment"].endswith(attachment_new.file.url)
        )
        agreement_updated = Agreement.objects.get(pk=agreement.pk)
        self.assertEqual(agreement_updated.attachment.last(), attachment_new)

    def test_patch_agreement_suspended(self):
        agreement = AgreementFactory(
            partner=self.partner1,
        )
        assert agreement.status != Agreement.SUSPENDED

        data = {
            "status": Agreement.SUSPENDED
        }
        mock_send = mock.Mock()
        send_path = "etools.applications.partners.utils.send_notification_with_template"
        with mock.patch(send_path, mock_send):
            status_code, response = self.run_request(
                agreement.pk,
                data,
                method="patch",
            )

        self.assertEqual(status_code, status.HTTP_200_OK)
        mock_send.assert_called()

    def test_terminate_no_doc(self):
        agreement = AgreementFactory(
            partner=self.partner1,
            status=Agreement.SIGNED,
        )
        self.assertEqual(agreement.status, Agreement.SIGNED)
        self.assertFalse(agreement.termination_doc.exists())
        data = {"status": Agreement.TERMINATED}
        status_code, response = self.run_request(
            agreement.pk,
            data,
            method="patch",
        )
        self.assertEqual(status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response,
            ["Cannot Transition without termination doc attached"],
        )
        # add termination document
        AttachmentFactory(
            content_object=agreement,
            code='partners_agreement_termination_doc',
        )
        self.assertTrue(agreement.termination_doc.exists())
        status_code, _ = self.run_request(agreement.pk, data, method="patch")
        self.assertEqual(status_code, status.HTTP_200_OK)
        agreement.refresh_from_db()
        self.assertEqual(agreement.status, Agreement.TERMINATED)
