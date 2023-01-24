from django.urls import resolve, reverse

from rest_framework import status
from rest_framework.test import APIRequestFactory

from etools.applications.attachments.tests.factories import AttachmentFactory, AttachmentFileTypeFactory
from etools.applications.audit.tests.factories import EngagementFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import PartnerType
from etools.applications.partners.tests.factories import (
    AgreementAmendmentFactory,
    AgreementFactory,
    AssessmentFactory,
    InterventionAmendmentFactory,
    InterventionFactory,
    InterventionResultLinkFactory,
    PartnerFactory,
)
from etools.applications.tpm.tests.factories import SimpleTPMPartnerFactory, TPMActivityFactory, TPMVisitFactory
from etools.applications.users.tests.factories import ProfileFactory, UserFactory


class TestAttachmentListView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.code_1 = "test_code_1"
        cls.file_type_1 = AttachmentFileTypeFactory()
        cls.code_2 = "test_code_2"
        cls.file_type_2 = AttachmentFileTypeFactory()
        cls.unicef_staff = UserFactory(is_staff=True)
        ProfileFactory(user=cls.unicef_staff)
        cls.user = UserFactory()
        cls.url = reverse("attachments:list")
        cls.attachment_1 = AttachmentFactory(
            file_type=cls.file_type_1,
            code=cls.code_1,
            file="sample1.pdf",
            content_object=cls.file_type_1,
            uploaded_by=cls.unicef_staff
        )
        cls.attachment_2 = AttachmentFactory(
            file_type=cls.file_type_2,
            code=cls.code_2,
            file="sample2.pdf",
            content_object=cls.file_type_2,
            uploaded_by=cls.user
        )

        cls.partner = PartnerFactory(
            partner_type=PartnerType.UN_AGENCY,
            vendor_number="V123",
        )
        cls.agreement = AgreementFactory(partner=cls.partner)
        cls.assessment = AssessmentFactory(partner=cls.partner)
        cls.amendment = AgreementAmendmentFactory(agreement=cls.agreement)
        cls.intervention = InterventionFactory(agreement=cls.agreement)
        cls.result_link = InterventionResultLinkFactory(
            intervention=cls.intervention
        )
        cls.intervention_amendment = InterventionAmendmentFactory(
            intervention=cls.intervention
        )
        cls.intervention_attachment = AttachmentFactory(
            file_type=cls.file_type_1,
            code=cls.code_1,
            file="sample1.pdf",
            content_object=cls.file_type_1,
            uploaded_by=cls.unicef_staff
        )

        cls.tpm_partner = SimpleTPMPartnerFactory(vendor_number="V432")
        cls.tpm_visit = TPMVisitFactory(tpm_partner=cls.tpm_partner)
        cls.tpm_activity = TPMActivityFactory(
            partner=cls.partner,
            intervention=cls.intervention,
            tpm_visit=cls.tpm_visit
        )

        cls.engagement = EngagementFactory(partner=cls.partner)

        cls.default_partner_response = [{
            "partner": "",
            "partner_type": "",
            "vendor_number": "",
            "pd_ssfa_number": "",
            "agreement_reference_number": "",
            "source": "",
        }] * 2

    def assert_keys(self, response):
        expected_keys = [
            "id",
            "partner",
            "partner_type",
            "vendor_number",
            "pd_ssfa",
            "pd_ssfa_number",
            "agreement_reference_number",
            "object_link",
            "filename",
            "file_type",
            "file_type_id",
            "file_link",
            "uploaded_by",
            "created",
            "attachment",
            "source",
            "ip_address"
        ]
        for row in response.data:
            self.assertCountEqual(list(row.keys()), expected_keys)

    def assert_values(self, response, expected):
        received = [{
            "partner": x["partner"],
            "partner_type": x["partner_type"],
            "vendor_number": x["vendor_number"],
            "pd_ssfa_number": x["pd_ssfa_number"],
            "agreement_reference_number": x["agreement_reference_number"],
            "source": x["source"],
        } for x in response.data]
        self.assertCountEqual(received, expected)

    def test_unauthenticated_user_forbidden(self):
        factory = APIRequestFactory()
        view_info = resolve(self.url)
        request = factory.get(self.url)
        response = view_info.func(request)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_schema_user(self):
        user = UserFactory(profile=None)
        response = self.forced_auth_req("get", self.url, user=user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_no_file(self):
        attachment = AttachmentFactory(
            file_type=self.file_type_1,
            code=self.code_1,
            content_object=self.file_type_1
        )
        self.assertFalse(attachment.file)
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assert_keys(response)

    def test_get_file(self):
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assert_keys(response)

    def test_get_hyperlink(self):
        attachment = AttachmentFactory(
            file_type=self.file_type_1,
            code=self.code_1,
            hyperlink="https://example.com/sample.pdf",
            content_object=self.file_type_1
        )
        self.assertTrue(attachment.hyperlink)
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assert_keys(response)

    def test_partner(self):
        code = "partners_partner_assessment"
        file_type = AttachmentFileTypeFactory()
        AttachmentFactory(
            file_type=file_type,
            code=code,
            file="sample1.pdf",
            content_object=self.partner,
            uploaded_by=self.user
        )
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assert_keys(response)
        self.assert_values(response, self.default_partner_response + [{
            "partner": self.partner.name,
            "partner_type": self.partner.partner_type,
            "vendor_number": self.partner.vendor_number,
            "pd_ssfa_number": "",
            "agreement_reference_number": "",
            "source": "Partnership Management Portal",
        }])

    def test_assessment(self):
        code = "partners_assessment_report"
        file_type = AttachmentFileTypeFactory()
        AttachmentFactory(
            file_type=file_type,
            code=code,
            file="sample1.pdf",
            content_object=self.assessment,
            uploaded_by=self.user
        )
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assert_keys(response)
        self.assert_values(response, self.default_partner_response + [{
            "partner": self.partner.name,
            "partner_type": self.partner.partner_type,
            "vendor_number": self.partner.vendor_number,
            "pd_ssfa_number": "",
            "agreement_reference_number": "",
            "source": "Partnership Management Portal",
        }])

    def test_agreement(self):
        code = "partners_agreement"
        file_type = AttachmentFileTypeFactory()
        AttachmentFactory(
            file_type=file_type,
            code=code,
            file="sample1.pdf",
            content_object=self.agreement,
            uploaded_by=self.user
        )
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assert_keys(response)
        self.assert_values(response, self.default_partner_response + [{
            "partner": self.partner.name,
            "partner_type": self.partner.partner_type,
            "vendor_number": self.partner.vendor_number,
            "pd_ssfa_number": "",
            "agreement_reference_number": self.agreement.reference_number,
            "source": "Partnership Management Portal",
        }])

    def test_agreement_amendment(self):
        code = "partners_agreement_amendment"
        file_type = AttachmentFileTypeFactory()
        AttachmentFactory(
            file_type=file_type,
            code=code,
            file="sample1.pdf",
            content_object=self.amendment,
            uploaded_by=self.user
        )
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assert_keys(response)
        self.assert_values(response, self.default_partner_response + [{
            "partner": self.partner.name,
            "partner_type": self.partner.partner_type,
            "vendor_number": self.partner.vendor_number,
            "pd_ssfa_number": "",
            "agreement_reference_number": self.amendment.agreement.reference_number,
            "source": "Partnership Management Portal",
        }])

    def test_intervention_amendment(self):
        code = "partners_intervention_amendment_signed"
        file_type = AttachmentFileTypeFactory()
        AttachmentFactory(
            file_type=file_type,
            code=code,
            file="sample1.pdf",
            content_object=self.intervention_amendment,
            uploaded_by=self.user
        )
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assert_keys(response)
        self.assert_values(response, self.default_partner_response + [{
            "partner": self.partner.name,
            "partner_type": self.partner.partner_type,
            "vendor_number": self.partner.vendor_number,
            "pd_ssfa_number": self.intervention.number,
            "agreement_reference_number": self.intervention.agreement.reference_number,
            "source": "Partnership Management Portal",
        }])

    def test_intervention_attachment(self):
        code = "partners_intervention_attachment"
        file_type = AttachmentFileTypeFactory()
        AttachmentFactory(
            file_type=file_type,
            code=code,
            file="sample1.pdf",
            content_object=self.intervention_attachment,
            uploaded_by=self.user
        )
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assert_keys(response)
        self.assert_values(response, self.default_partner_response + [{
            "partner": self.partner.name,
            "partner_type": self.partner.partner_type,
            "vendor_number": self.partner.vendor_number,
            "pd_ssfa_number": self.intervention.number,
            "agreement_reference_number": self.intervention.agreement.reference_number,
            "source": "Partnership Management Portal",
        }])
        self.assertCountEqual([x["file_type"] for x in response.data], [
            self.file_type_1.label,
            self.file_type_2.label,
            self.intervention_attachment.type.name
        ])

    def test_intervention(self):
        code_prc = "partners_intervention_prc_review"
        file_type_prc = AttachmentFileTypeFactory()
        code_pd = "partners_intervention_signed_pd"
        file_type_pd = AttachmentFileTypeFactory()
        AttachmentFactory(
            file_type=file_type_prc,
            code=code_prc,
            file="sample1.pdf",
            content_object=self.intervention,
            uploaded_by=self.user
        )
        AttachmentFactory(
            file_type=file_type_pd,
            code=code_pd,
            file="sample1.pdf",
            content_object=self.intervention,
            uploaded_by=self.user
        )
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)
        self.assert_keys(response)
        self.assert_values(response, self.default_partner_response + [{
            "partner": self.partner.name,
            "partner_type": self.partner.partner_type,
            "vendor_number": self.partner.vendor_number,
            "pd_ssfa_number": self.intervention.number,
            "agreement_reference_number": self.intervention.agreement.reference_number,
            "source": "Partnership Management Portal",
        }, {
            "partner": self.partner.name,
            "partner_type": self.partner.partner_type,
            "vendor_number": self.partner.vendor_number,
            "pd_ssfa_number": self.intervention.number,
            "agreement_reference_number": self.intervention.agreement.reference_number,
            "source": "Partnership Management Portal",
        }])

    def test_tpm_activity_attachments(self):
        code = "activity_attachments"
        file_type = AttachmentFileTypeFactory(label="Activity Attachment")
        AttachmentFactory(
            file_type=file_type,
            code=code,
            file="sample3.pdf",
            content_object=self.tpm_activity,
            uploaded_by=self.user
        )
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assert_keys(response)
        self.assert_values(response, self.default_partner_response + [{
            "partner": self.partner.name,
            "partner_type": self.partner.partner_type,
            "vendor_number": self.partner.vendor_number,
            "pd_ssfa_number": self.intervention.number,
            "agreement_reference_number": self.intervention.agreement.reference_number,
            "source": "Third Party Monitoring",
        }])
        self.assertCountEqual([x["file_type"] for x in response.data], [
            self.file_type_1.label,
            self.file_type_2.label,
            file_type.label
        ])

    def test_tpm_activity_report_attachments(self):
        code = "activity_report"
        file_type = AttachmentFileTypeFactory(label="Activity Report")
        AttachmentFactory(
            file_type=file_type,
            code=code,
            file="sample3.pdf",
            content_object=self.tpm_activity,
            uploaded_by=self.user
        )
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assert_keys(response)
        self.assert_values(response, self.default_partner_response + [{
            "partner": self.partner.name,
            "partner_type": self.partner.partner_type,
            "vendor_number": self.partner.vendor_number,
            "pd_ssfa_number": self.intervention.number,
            "agreement_reference_number": self.intervention.agreement.reference_number,
            "source": "Third Party Monitoring",
        }])
        self.assertCountEqual([x["file_type"] for x in response.data], [
            self.file_type_1.label,
            self.file_type_2.label,
            file_type.label
        ])

    def test_audit_engagement_attachments(self):
        code = "audit_engagement"
        file_type = AttachmentFileTypeFactory(label="Audit Engagement")
        AttachmentFactory(
            file_type=file_type,
            code=code,
            file="sample3.pdf",
            content_object=self.engagement,
            uploaded_by=self.user
        )
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assert_keys(response)
        self.assert_values(response, self.default_partner_response + [{
            "partner": self.partner.name,
            "partner_type": self.partner.partner_type,
            "vendor_number": self.partner.vendor_number,
            "pd_ssfa_number": "",
            "agreement_reference_number": self.engagement.reference_number,
            "source": "Financial Assurance (FAM)",
        }])
        self.assertCountEqual([x["file_type"] for x in response.data], [
            self.file_type_1.label,
            self.file_type_2.label,
            file_type.label
        ])

    def test_audit_engagement_report_attachments(self):
        code = "audit_report"
        file_type = AttachmentFileTypeFactory(label="Audit Report")
        AttachmentFactory(
            file_type=file_type,
            code=code,
            file="sample3.pdf",
            content_object=self.engagement,
            uploaded_by=self.user
        )
        response = self.forced_auth_req(
            "get",
            self.url,
            user=self.unicef_staff,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assert_keys(response)
        self.assert_values(response, self.default_partner_response + [{
            "partner": self.partner.name,
            "partner_type": self.partner.partner_type,
            "vendor_number": self.partner.vendor_number,
            "pd_ssfa_number": "",
            "agreement_reference_number": self.engagement.reference_number,
            "source": "Financial Assurance (FAM)",
        }])
        self.assertCountEqual([x["file_type"] for x in response.data], [
            self.file_type_1.label,
            self.file_type_2.label,
            file_type.label
        ])
