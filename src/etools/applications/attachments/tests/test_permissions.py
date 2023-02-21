from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection

from rest_framework import status

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.audit.tests.factories import AuditorUserFactory, AuditPartnerFactory, SpecialAuditFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.data_collection.tests.factories import (
    ChecklistOverallFindingFactory,
    StartedChecklistFactory,
)
from etools.applications.field_monitoring.fm_settings.models import GlobalConfig
from etools.applications.field_monitoring.fm_settings.tests.factories import LogIssueFactory
from etools.applications.field_monitoring.groups import FMUser
from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.field_monitoring.planning.tests.factories import MonitoringActivityFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.psea.models import Assessor
from etools.applications.psea.tests.factories import AnswerFactory, AssessmentFactory, AssessorFactory
from etools.applications.tpm.tests.factories import (
    TPMActivityFactory,
    TPMPartnerFactory,
    TPMUserFactory,
    TPMVisitFactory,
)
from etools.applications.users.tests.factories import UserFactory
from etools.libraries.djangolib.models import GroupWrapper


class DownloadAttachmentsBaseTestCase(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        # clearing groups cache
        GroupWrapper.invalidate_instances()

        self.unicef_user = UserFactory(is_staff=True)
        self.attachment = AttachmentFactory(
            file=SimpleUploadedFile(
                'simple_file.txt',
                b'these are the file contents!'
            )
        )

    def _test_download(self, attachment, user, expected_status):
        response = self.forced_auth_req('get', attachment.file_link, user=user)
        self.assertEqual(response.status_code, expected_status)
        return response


class DownloadAPAttachmentTestCase(DownloadAttachmentsBaseTestCase):
    def setUp(self):
        super().setUp()
        self.auditor_firm = AuditPartnerFactory()
        self.auditor = AuditorUserFactory(partner_firm=self.auditor_firm, is_staff=False,
                                          profile__countries_available=[connection.tenant],
                                          profile__country=connection.tenant)
        self.specialaudit = SpecialAuditFactory()
        self.attachment.content_object = self.specialaudit
        self.attachment.save()

    def test_attachment_user_not_in_schema(self):
        another_schema_user = UserFactory(is_staff=True, profile__countries_available=[], profile__country=None)
        self._test_download(self.attachment, another_schema_user, status.HTTP_403_FORBIDDEN)

    def test_attachment_unicef(self):
        self._test_download(self.attachment, self.unicef_user, status.HTTP_302_FOUND)

    def test_attachment_authorized_officer(self):
        self.specialaudit.staff_members.add(self.auditor.purchase_order_auditorstaffmember)
        self._test_download(self.attachment, self.auditor, status.HTTP_302_FOUND)

    def test_attachment_unrelated_auditor(self):
        self._test_download(self.attachment, self.auditor, status.HTTP_403_FORBIDDEN)


class DownloadTPMVisitAttachmentTestCase(DownloadAttachmentsBaseTestCase):
    def setUp(self):
        super().setUp()
        self.tpm_organization = TPMPartnerFactory()
        self.tpm_staff = TPMUserFactory(tpm_partner=self.tpm_organization, is_staff=False,
                                        profile__countries_available=[connection.tenant],
                                        profile__country=connection.tenant)
        self.visit = TPMVisitFactory(tpm_partner=self.tpm_organization)
        self.attachment.content_object = self.visit
        self.attachment.save()

    def test_attachment_user_not_in_schema(self):
        another_schema_user = UserFactory(is_staff=True, profile__countries_available=[], profile__country=None)
        self._test_download(self.attachment, another_schema_user, status.HTTP_403_FORBIDDEN)

    def test_attachment_unicef(self):
        self._test_download(self.attachment, self.unicef_user, status.HTTP_302_FOUND)

    def test_attachment_staff_member(self):
        self._test_download(self.attachment, self.tpm_staff, status.HTTP_302_FOUND)

    def test_attachment_unrelated_staff(self):
        another_tpm_staff = TPMUserFactory(is_staff=False, profile__countries_available=[connection.tenant],
                                           profile__country=connection.tenant)
        self._test_download(self.attachment, another_tpm_staff, status.HTTP_403_FORBIDDEN)


class DownloadTPMVisitActivityAttachmentTestCase(DownloadAttachmentsBaseTestCase):
    def setUp(self):
        super().setUp()
        self.tpm_organization = TPMPartnerFactory()
        self.tpm_staff = TPMUserFactory(tpm_partner=self.tpm_organization, is_staff=False,
                                        profile__countries_available=[connection.tenant],
                                        profile__country=connection.tenant)
        self.visit = TPMVisitFactory(tpm_partner=self.tpm_organization)
        self.activity = TPMActivityFactory(tpm_visit=self.visit)
        self.attachment.content_object = self.activity
        self.attachment.save()

    def test_attachment_user_not_in_schema(self):
        another_schema_user = UserFactory(is_staff=True, profile__countries_available=[], profile__country=None)
        self._test_download(self.attachment, another_schema_user, status.HTTP_403_FORBIDDEN)

    def test_attachment_unicef(self):
        self._test_download(self.attachment, self.unicef_user, status.HTTP_302_FOUND)

    def test_attachment_staff_member(self):
        self._test_download(self.attachment, self.tpm_staff, status.HTTP_302_FOUND)

    def test_attachment_unrelated_staff(self):
        another_tpm_staff = TPMUserFactory(is_staff=False, profile__countries_available=[connection.tenant],
                                           profile__country=connection.tenant)
        self._test_download(self.attachment, another_tpm_staff, status.HTTP_403_FORBIDDEN)


class DownloadTPMPartnerAttachmentTestCase(DownloadAttachmentsBaseTestCase):
    def setUp(self):
        super().setUp()
        self.tpm_organization = TPMPartnerFactory()
        self.tpm_staff = TPMUserFactory(tpm_partner=self.tpm_organization, is_staff=False,
                                        profile__countries_available=[connection.tenant],
                                        profile__country=connection.tenant)
        self.attachment.content_object = self.tpm_organization
        self.attachment.save()

    def test_attachment_user_not_in_schema(self):
        another_schema_user = UserFactory(is_staff=True, profile__countries_available=[], profile__country=None)
        self._test_download(self.attachment, another_schema_user, status.HTTP_403_FORBIDDEN)

    def test_attachment_unicef(self):
        self._test_download(self.attachment, self.unicef_user, status.HTTP_302_FOUND)

    def test_attachment_staff_member(self):
        self._test_download(self.attachment, self.tpm_staff, status.HTTP_302_FOUND)

    def test_attachment_unrelated_staff(self):
        another_tpm_staff = TPMUserFactory(is_staff=False, profile__countries_available=[connection.tenant],
                                           profile__country=connection.tenant)
        self._test_download(self.attachment, another_tpm_staff, status.HTTP_403_FORBIDDEN)


class DownloadFMGlobalConfigAttachmentTestCase(DownloadAttachmentsBaseTestCase):
    def setUp(self):
        super().setUp()
        self.tpm_organization = TPMPartnerFactory()
        self.fm_user = UserFactory(is_staff=False,
                                   profile__countries_available=[connection.tenant],
                                   profile__country=connection.tenant,
                                   groups__data=[FMUser.name])
        self.config = GlobalConfig.get_current()
        self.attachment.content_object = self.config
        self.attachment.save()

    def test_attachment_user_not_in_schema(self):
        another_schema_user = UserFactory(is_staff=True, profile__countries_available=[], profile__country=None)
        self._test_download(self.attachment, another_schema_user, status.HTTP_403_FORBIDDEN)

    def test_attachment_unicef(self):
        self._test_download(self.attachment, self.unicef_user, status.HTTP_302_FOUND)

    def test_attachment_fm_user(self):
        self._test_download(self.attachment, self.fm_user, status.HTTP_302_FOUND)

    def test_attachment_not_fm_user(self):
        user = UserFactory(is_staff=False,
                           profile__countries_available=[connection.tenant],
                           profile__country=connection.tenant,
                           groups__data=["Unknown"])
        self._test_download(self.attachment, user, status.HTTP_403_FORBIDDEN)


class DownloadFMLogIssueAttachmentTestCase(DownloadAttachmentsBaseTestCase):
    def setUp(self):
        super().setUp()
        self.tpm_organization = TPMPartnerFactory()
        self.fm_user = UserFactory(is_staff=False,
                                   profile__countries_available=[connection.tenant],
                                   profile__country=connection.tenant,
                                   groups__data=[FMUser.name])
        self.log_issue = LogIssueFactory(partner=PartnerFactory())
        self.attachment.content_object = self.log_issue
        self.attachment.save()

    def test_attachment_user_not_in_schema(self):
        another_schema_user = UserFactory(is_staff=True, profile__countries_available=[], profile__country=None)
        self._test_download(self.attachment, another_schema_user, status.HTTP_403_FORBIDDEN)

    def test_attachment_unicef(self):
        self._test_download(self.attachment, self.unicef_user, status.HTTP_302_FOUND)

    def test_attachment_fm_user(self):
        self._test_download(self.attachment, self.fm_user, status.HTTP_302_FOUND)

    def test_attachment_not_fm_user(self):
        user = UserFactory(is_staff=False,
                           profile__countries_available=[connection.tenant],
                           profile__country=connection.tenant,
                           groups__data=["Unknown"])
        self._test_download(self.attachment, user, status.HTTP_403_FORBIDDEN)


class DownloadFMActivityAttachmentTestCase(DownloadAttachmentsBaseTestCase):
    def setUp(self):
        super().setUp()
        self.tpm_organization = TPMPartnerFactory()
        self.tpm_staff = TPMUserFactory(tpm_partner=self.tpm_organization, is_staff=False,
                                        profile__countries_available=[connection.tenant],
                                        profile__country=connection.tenant)
        self.activity = MonitoringActivityFactory(
            tpm_partner=self.tpm_organization,
            monitor_type=MonitoringActivity.MONITOR_TYPE_CHOICES.tpm,
        )
        self.attachment.content_object = self.activity
        self.attachment.save()

    def test_attachment_user_not_in_schema(self):
        another_schema_user = UserFactory(is_staff=True, profile__countries_available=[], profile__country=None)
        self._test_download(self.attachment, another_schema_user, status.HTTP_403_FORBIDDEN)

    def test_attachment_unicef(self):
        self._test_download(self.attachment, self.unicef_user, status.HTTP_302_FOUND)

    def test_attachment_visit_lead(self):
        self.activity.visit_lead = self.tpm_staff
        self.activity.save()
        self._test_download(self.attachment, self.tpm_staff, status.HTTP_302_FOUND)

    def test_attachment_team_member(self):
        self.activity.team_members.add(self.tpm_staff)
        self._test_download(self.attachment, self.tpm_staff, status.HTTP_302_FOUND)

    def test_attachment_unrelated_staff(self):
        self._test_download(self.attachment, self.tpm_staff, status.HTTP_403_FORBIDDEN)


class DownloadFMActivityCheckListAttachmentTestCase(DownloadAttachmentsBaseTestCase):
    def setUp(self):
        super().setUp()
        self.tpm_organization = TPMPartnerFactory()
        self.tpm_staff = TPMUserFactory(tpm_partner=self.tpm_organization, is_staff=False,
                                        profile__countries_available=[connection.tenant],
                                        profile__country=connection.tenant)
        self.activity = MonitoringActivityFactory(
            tpm_partner=self.tpm_organization,
            monitor_type=MonitoringActivity.MONITOR_TYPE_CHOICES.tpm,
        )
        self.started_checklist = StartedChecklistFactory(monitoring_activity=self.activity)
        self.checklist_overall_finding = ChecklistOverallFindingFactory(
            started_checklist=self.started_checklist,
            partner=PartnerFactory(),
        )
        self.attachment.content_object = self.checklist_overall_finding
        self.attachment.save()

    def test_attachment_user_not_in_schema(self):
        another_schema_user = UserFactory(is_staff=True, profile__countries_available=[], profile__country=None)
        self._test_download(self.attachment, another_schema_user, status.HTTP_403_FORBIDDEN)

    def test_attachment_unicef(self):
        self._test_download(self.attachment, self.unicef_user, status.HTTP_302_FOUND)

    def test_attachment_visit_lead(self):
        self.activity.visit_lead = self.tpm_staff
        self.activity.save()
        self._test_download(self.attachment, self.tpm_staff, status.HTTP_302_FOUND)

    def test_attachment_team_member(self):
        self.activity.team_members.add(self.tpm_staff)
        self._test_download(self.attachment, self.tpm_staff, status.HTTP_302_FOUND)

    def test_attachment_unrelated_staff(self):
        self._test_download(self.attachment, self.tpm_staff, status.HTTP_403_FORBIDDEN)


class DownloadPSEAAssessmentAttachmentTestCase(DownloadAttachmentsBaseTestCase):
    def setUp(self):
        super().setUp()
        self.auditor_firm = AuditPartnerFactory()
        self.auditor = AuditorUserFactory(partner_firm=self.auditor_firm, is_staff=False,
                                          profile__countries_available=[connection.tenant],
                                          profile__country=connection.tenant)
        self.assessment = AssessmentFactory()
        self.attachment.content_object = self.assessment
        self.attachment.save()

    def test_attachment_user_not_in_schema(self):
        another_schema_user = UserFactory(is_staff=True, profile__countries_available=[], profile__country=None)
        self._test_download(self.attachment, another_schema_user, status.HTTP_403_FORBIDDEN)

    def test_attachment_unicef(self):
        self._test_download(self.attachment, self.unicef_user, status.HTTP_302_FOUND)

    def test_attachment_external_accessor(self):
        external_user = UserFactory(
            is_staff=False,
            profile__countries_available=[connection.tenant],
            profile__country=connection.tenant,
            groups__data=[],
        )
        AssessorFactory(
            assessment=self.assessment,
            assessor_type=Assessor.TYPE_EXTERNAL,
            user=external_user,
        )
        self._test_download(self.attachment, external_user, status.HTTP_302_FOUND)

    def test_attachment_unrelated_staff(self):
        AssessorFactory(
            assessment=self.assessment,
            assessor_type=Assessor.TYPE_EXTERNAL,
            auditor_firm=self.auditor_firm,
            user=None,
        )
        self._test_download(self.attachment, self.auditor, status.HTTP_403_FORBIDDEN)

    def test_attachment_staff(self):
        assessor = AssessorFactory(
            assessment=self.assessment,
            assessor_type=Assessor.TYPE_EXTERNAL,
            auditor_firm=self.auditor_firm,
            user=None,
        )
        assessor.auditor_firm_staff.add(self.auditor.purchase_order_auditorstaffmember)
        self._test_download(self.attachment, self.auditor, status.HTTP_302_FOUND)


class DownloadPSEAAnswerAttachmentTestCase(DownloadAttachmentsBaseTestCase):
    def setUp(self):
        super().setUp()
        self.auditor_firm = AuditPartnerFactory()
        self.auditor = AuditorUserFactory(partner_firm=self.auditor_firm, is_staff=False,
                                          profile__countries_available=[connection.tenant],
                                          profile__country=connection.tenant)
        self.assessment = AssessmentFactory()
        self.answer = AnswerFactory(assessment=self.assessment)
        self.attachment.content_object = self.answer
        self.attachment.save()

    def test_attachment_user_not_in_schema(self):
        another_schema_user = UserFactory(is_staff=True, profile__countries_available=[], profile__country=None)
        self._test_download(self.attachment, another_schema_user, status.HTTP_403_FORBIDDEN)

    def test_attachment_unicef(self):
        self._test_download(self.attachment, self.unicef_user, status.HTTP_302_FOUND)

    def test_attachment_external_accessor(self):
        external_user = UserFactory(
            is_staff=False,
            profile__countries_available=[connection.tenant],
            profile__country=connection.tenant,
            groups__data=[],
        )
        AssessorFactory(
            assessment=self.assessment,
            assessor_type=Assessor.TYPE_EXTERNAL,
            user=external_user,
        )
        self._test_download(self.attachment, external_user, status.HTTP_302_FOUND)

    def test_attachment_unrelated_staff(self):
        AssessorFactory(
            assessment=self.assessment,
            assessor_type=Assessor.TYPE_EXTERNAL,
            auditor_firm=self.auditor_firm,
            user=None,
        )
        self._test_download(self.attachment, self.auditor, status.HTTP_403_FORBIDDEN)

    def test_attachment_staff(self):
        assessor = AssessorFactory(
            assessment=self.assessment,
            assessor_type=Assessor.TYPE_EXTERNAL,
            auditor_firm=self.auditor_firm,
            user=None,
        )
        assessor.auditor_firm_staff.add(self.auditor.purchase_order_auditorstaffmember)
        self._test_download(self.attachment, self.auditor, status.HTTP_302_FOUND)
