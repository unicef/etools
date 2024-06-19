from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.urls import reverse

from rest_framework import status

from etools.applications.attachments.tests.factories import AttachmentFactory, AttachmentLinkFactory
from etools.applications.audit.models import Auditor
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
from etools.applications.partners.permissions import UNICEF_USER
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.psea.models import Assessor
from etools.applications.psea.tests.factories import AnswerFactory, AssessmentFactory, AssessorFactory
from etools.applications.tpm.models import ThirdPartyMonitor
from etools.applications.tpm.tests.factories import (
    TPMActivityFactory,
    TPMPartnerFactory,
    TPMUserFactory,
    TPMVisitFactory,
)
from etools.applications.users.tests.factories import DummyCountryFactory, GroupFactory, RealmFactory, UserFactory
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


class DownloadUnlinkedAttachmentTestCase(DownloadAttachmentsBaseTestCase):
    # anyone has access to attachment when it's not linked to any object

    def test_attachment_user_not_in_schema(self):
        another_schema_user = UserFactory(is_staff=True, realms__data=[], profile__country=None)
        self._test_download(self.attachment, another_schema_user, status.HTTP_403_FORBIDDEN)

    def test_attachment_user_in_different_schema(self):
        other_country = DummyCountryFactory()
        self.assertNotEqual(other_country.pk, connection.tenant.pk)
        another_schema_user = UserFactory(is_staff=True)
        another_schema_user.realms.update(is_active=False)
        RealmFactory(user=another_schema_user, country=other_country, group=GroupFactory(name=UNICEF_USER))
        self._test_download(self.attachment, another_schema_user, status.HTTP_403_FORBIDDEN)

    def test_attachment_unicef(self):
        self._test_download(self.attachment, self.unicef_user, status.HTTP_302_FOUND)

    def test_attachment_auditor(self):
        auditor = AuditorUserFactory(is_staff=False)
        self._test_download(self.attachment, auditor, status.HTTP_302_FOUND)


class DownloadAPAttachmentTestCase(DownloadAttachmentsBaseTestCase):
    def setUp(self):
        super().setUp()
        self.auditor_firm = AuditPartnerFactory()
        self.specialaudit = SpecialAuditFactory(agreement__auditor_firm=self.auditor_firm)
        self.auditor = AuditorUserFactory(partner_firm=self.auditor_firm, is_staff=False)
        self.attachment.content_object = self.specialaudit
        self.attachment.save()

    def test_attachment_user_not_in_schema(self):
        another_schema_user = UserFactory(is_staff=True, realms__data=[], profile__country=None)
        self._test_download(self.attachment, another_schema_user, status.HTTP_403_FORBIDDEN)

    def test_attachment_unicef(self):
        self._test_download(self.attachment, self.unicef_user, status.HTTP_302_FOUND)

    def test_attachment_authorized_officer(self):
        self.specialaudit.staff_members.add(self.auditor)
        self._test_download(self.attachment, self.auditor, status.HTTP_302_FOUND)

    def test_attachment_unrelated_auditor(self):
        self._test_download(self.attachment, self.auditor, status.HTTP_403_FORBIDDEN)

    def test_attachment_deactivated_auditor(self):
        auditor = AuditorUserFactory(partner_firm=self.auditor_firm, is_staff=False)
        self.specialaudit.staff_members.add(auditor)
        auditor.realms.update(is_active=False)
        self._test_download(self.attachment, auditor, status.HTTP_403_FORBIDDEN)

    def test_attachment_moved_auditor(self):
        # user should have no access if not active in the organization
        #   even if it's listed in the audit and has active realm with Auditor group
        auditor_firm = AuditPartnerFactory()
        auditor = AuditorUserFactory(partner_firm=auditor_firm, is_staff=False)
        self.specialaudit.staff_members.add(auditor)
        realm = RealmFactory(
            user=auditor,
            country=self.tenant,
            organization=self.auditor_firm.organization,
            group=Auditor.as_group()
        )
        realm.is_active = False
        realm.save()
        self._test_download(self.attachment, auditor, status.HTTP_403_FORBIDDEN)


class DownloadTPMVisitAttachmentTestCase(DownloadAttachmentsBaseTestCase):
    def setUp(self):
        super().setUp()
        self.tpm_organization = TPMPartnerFactory()
        self.visit = TPMVisitFactory(tpm_partner=self.tpm_organization)
        self.tpm_staff = TPMUserFactory(tpm_partner=self.tpm_organization, is_staff=False)
        self.attachment.content_object = self.visit
        self.attachment.save()

    def test_attachment_user_not_in_schema(self):
        another_schema_user = UserFactory(is_staff=True, realms__data=[], profile__country=None)
        self._test_download(self.attachment, another_schema_user, status.HTTP_403_FORBIDDEN)

    def test_attachment_unicef(self):
        self._test_download(self.attachment, self.unicef_user, status.HTTP_302_FOUND)

    def test_attachment_staff_member(self):
        self._test_download(self.attachment, self.tpm_staff, status.HTTP_302_FOUND)

    def test_attachment_unrelated_staff(self):
        another_tpm_staff = TPMUserFactory(is_staff=False)
        self._test_download(self.attachment, another_tpm_staff, status.HTTP_403_FORBIDDEN)

    def test_attachment_deactivated_staff(self):
        staff = TPMUserFactory(tpm_partner=self.tpm_organization, is_staff=False)
        self.visit.tpm_partner_focal_points.add(staff)
        staff.realms.update(is_active=False)
        self._test_download(self.attachment, staff, status.HTTP_403_FORBIDDEN)

    def test_attachment_moved_staff(self):
        # user should have no access if not active in the organization
        #   even if it's listed in the visit and has active realm with TPM group
        tpm_organization = TPMPartnerFactory()
        staff = TPMUserFactory(tpm_partner=tpm_organization, is_staff=False)
        self.visit.tpm_partner_focal_points.add(staff)
        realm = RealmFactory(
            user=staff,
            country=self.tenant,
            organization=self.tpm_organization.organization,
            group=ThirdPartyMonitor.as_group()
        )
        realm.is_active = False
        realm.save()
        self._test_download(self.attachment, staff, status.HTTP_403_FORBIDDEN)


class DownloadTPMVisitActivityAttachmentTestCase(DownloadAttachmentsBaseTestCase):
    def setUp(self):
        super().setUp()
        self.tpm_organization = TPMPartnerFactory()
        self.visit = TPMVisitFactory(tpm_partner=self.tpm_organization)
        self.tpm_staff = TPMUserFactory(tpm_partner=self.tpm_organization, is_staff=False)
        self.activity = TPMActivityFactory(tpm_visit=self.visit)
        self.attachment.content_object = self.activity
        self.attachment.save()

    def test_attachment_user_not_in_schema(self):
        another_schema_user = UserFactory(is_staff=True, realms__data=[], profile__country=None)
        self._test_download(self.attachment, another_schema_user, status.HTTP_403_FORBIDDEN)

    def test_attachment_unicef(self):
        self._test_download(self.attachment, self.unicef_user, status.HTTP_302_FOUND)

    def test_attachment_staff_member(self):
        self._test_download(self.attachment, self.tpm_staff, status.HTTP_302_FOUND)

    def test_attachment_unrelated_staff(self):
        another_tpm_staff = TPMUserFactory(is_staff=False)
        self._test_download(self.attachment, another_tpm_staff, status.HTTP_403_FORBIDDEN)

    def test_attachment_deactivated_staff(self):
        staff = TPMUserFactory(tpm_partner=self.tpm_organization, is_staff=False)
        self.visit.tpm_partner_focal_points.add(staff)
        staff.realms.update(is_active=False)
        self._test_download(self.attachment, staff, status.HTTP_403_FORBIDDEN)

    def test_attachment_moved_staff(self):
        # user should have no access if not active in the organization
        #   even if it's listed in the visit and has active realm with TPM group
        tpm_organization = TPMPartnerFactory()
        staff = TPMUserFactory(tpm_partner=tpm_organization, is_staff=False)
        self.visit.tpm_partner_focal_points.add(staff)
        realm = RealmFactory(
            user=staff,
            country=self.tenant,
            organization=self.tpm_organization.organization,
            group=ThirdPartyMonitor.as_group()
        )
        realm.is_active = False
        realm.save()
        self._test_download(self.attachment, staff, status.HTTP_403_FORBIDDEN)


class DownloadTPMPartnerAttachmentTestCase(DownloadAttachmentsBaseTestCase):
    def setUp(self):
        super().setUp()
        self.tpm_organization = TPMPartnerFactory()
        self.tpm_staff = TPMUserFactory(tpm_partner=self.tpm_organization, is_staff=False)
        self.attachment.content_object = self.tpm_organization
        self.attachment.save()

    def test_attachment_user_not_in_schema(self):
        another_schema_user = UserFactory(is_staff=True, realms__data=[], profile__country=None)
        self._test_download(self.attachment, another_schema_user, status.HTTP_403_FORBIDDEN)

    def test_attachment_unicef(self):
        self._test_download(self.attachment, self.unicef_user, status.HTTP_302_FOUND)

    def test_attachment_staff_member(self):
        self._test_download(self.attachment, self.tpm_staff, status.HTTP_302_FOUND)

    def test_attachment_unrelated_staff(self):
        another_tpm_staff = TPMUserFactory(is_staff=False)
        self._test_download(self.attachment, another_tpm_staff, status.HTTP_403_FORBIDDEN)

    def test_attachment_deactivated_staff(self):
        staff = TPMUserFactory(tpm_partner=self.tpm_organization, is_staff=False)
        staff.realms.update(is_active=False)
        self._test_download(self.attachment, staff, status.HTTP_403_FORBIDDEN)

    def test_attachment_moved_staff(self):
        # user should have no access if not active in the organization
        #   even if it's listed in the visit and has active realm with TPM group
        tpm_organization = TPMPartnerFactory()
        staff = TPMUserFactory(tpm_partner=tpm_organization, is_staff=False)
        realm = RealmFactory(
            user=staff,
            country=self.tenant,
            organization=self.tpm_organization.organization,
            group=ThirdPartyMonitor.as_group()
        )
        realm.is_active = False
        realm.save()
        self._test_download(self.attachment, staff, status.HTTP_403_FORBIDDEN)


class DownloadFMGlobalConfigAttachmentTestCase(DownloadAttachmentsBaseTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = GlobalConfig.get_current()

    def setUp(self):
        super().setUp()
        # FM user is always UNICEF user
        self.fm_user = UserFactory(is_staff=False, realms__data=[UNICEF_USER, FMUser.name])
        self.attachment.content_object = self.config
        self.attachment.save()

    def test_attachment_user_not_in_schema(self):
        another_schema_user = UserFactory(is_staff=True, realms__data=[], profile__country=None)
        self._test_download(self.attachment, another_schema_user, status.HTTP_403_FORBIDDEN)

    def test_attachment_unicef(self):
        self._test_download(self.attachment, self.unicef_user, status.HTTP_302_FOUND)

    def test_attachment_fm_user(self):
        self._test_download(self.attachment, self.fm_user, status.HTTP_302_FOUND)

    def test_attachment_not_fm_user(self):
        user = UserFactory(is_staff=False, realms__data=["Unknown"])
        self._test_download(self.attachment, user, status.HTTP_403_FORBIDDEN)


class DownloadFMLogIssueAttachmentTestCase(DownloadAttachmentsBaseTestCase):
    def setUp(self):
        super().setUp()
        self.tpm_organization = TPMPartnerFactory()
        # FM user is always UNICEF user
        self.fm_user = UserFactory(is_staff=False, realms__data=[UNICEF_USER, FMUser.name])
        self.log_issue = LogIssueFactory(partner=PartnerFactory())
        self.attachment.content_object = self.log_issue
        self.attachment.save()

    def test_attachment_user_not_in_schema(self):
        another_schema_user = UserFactory(is_staff=True, realms__data=[], profile__country=None)
        self._test_download(self.attachment, another_schema_user, status.HTTP_403_FORBIDDEN)

    def test_attachment_unicef(self):
        self._test_download(self.attachment, self.unicef_user, status.HTTP_302_FOUND)

    def test_attachment_fm_user(self):
        self._test_download(self.attachment, self.fm_user, status.HTTP_302_FOUND)

    def test_attachment_not_fm_user(self):
        user = UserFactory(is_staff=False, realms__data=["Unknown"])
        self._test_download(self.attachment, user, status.HTTP_403_FORBIDDEN)


class DownloadFMActivityAttachmentTestCase(DownloadAttachmentsBaseTestCase):
    def setUp(self):
        super().setUp()
        self.tpm_organization = TPMPartnerFactory()
        self.tpm_staff = TPMUserFactory(tpm_partner=self.tpm_organization, is_staff=False)
        self.activity = MonitoringActivityFactory(
            tpm_partner=self.tpm_organization,
            monitor_type=MonitoringActivity.MONITOR_TYPE_CHOICES.tpm,
        )
        self.attachment.content_object = self.activity
        self.attachment.save()

    def test_attachment_user_not_in_schema(self):
        another_schema_user = UserFactory(is_staff=True, realms__data=[], profile__country=None)
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
        self.tpm_staff = TPMUserFactory(tpm_partner=self.tpm_organization, is_staff=False)
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
        another_schema_user = UserFactory(is_staff=True, realms__data=[], profile__country=None)
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
        self.auditor = AuditorUserFactory(partner_firm=self.auditor_firm, is_staff=False)
        self.assessment = AssessmentFactory()
        self.attachment.content_object = self.assessment
        self.attachment.save()

    def test_attachment_user_not_in_schema(self):
        another_schema_user = UserFactory(is_staff=True, realms__data=[], profile__country=None)
        self._test_download(self.attachment, another_schema_user, status.HTTP_403_FORBIDDEN)

    def test_attachment_unicef(self):
        self._test_download(self.attachment, self.unicef_user, status.HTTP_302_FOUND)

    def test_attachment_external_accessor(self):
        external_user = UserFactory(
            is_staff=False, realms__data=[Auditor.name]
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
            assessor_type=Assessor.TYPE_VENDOR,
            auditor_firm=self.auditor_firm,
            user=None,
        )
        self._test_download(self.attachment, self.auditor, status.HTTP_403_FORBIDDEN)

    def test_attachment_staff(self):
        assessor = AssessorFactory(
            assessment=self.assessment,
            assessor_type=Assessor.TYPE_VENDOR,
            auditor_firm=self.auditor_firm,
            user=None,
        )
        assessor.auditor_firm_staff.add(self.auditor)
        self._test_download(self.attachment, self.auditor, status.HTTP_302_FOUND)


class DownloadPSEAAnswerAttachmentTestCase(DownloadAttachmentsBaseTestCase):
    def setUp(self):
        super().setUp()
        self.auditor_firm = AuditPartnerFactory()
        self.auditor = AuditorUserFactory(partner_firm=self.auditor_firm, is_staff=False)
        self.assessment = AssessmentFactory()
        self.answer = AnswerFactory(assessment=self.assessment)
        self.attachment.content_object = self.answer
        self.attachment.save()

    def test_attachment_user_not_in_schema(self):
        another_schema_user = UserFactory(is_staff=True, realms__data=[], profile__country=None)
        self._test_download(self.attachment, another_schema_user, status.HTTP_403_FORBIDDEN)

    def test_attachment_unicef(self):
        AssessorFactory(
            assessment=self.assessment,
            assessor_type=Assessor.TYPE_UNICEF,
        )
        self._test_download(self.attachment, self.unicef_user, status.HTTP_302_FOUND)

    def test_attachment_unicef_auditor(self):
        AssessorFactory(
            assessment=self.assessment,
            assessor_type=Assessor.TYPE_UNICEF,
        )
        self._test_download(self.attachment, self.auditor, status.HTTP_403_FORBIDDEN)

    def test_attachment_external_accessor(self):
        external_user = UserFactory(is_staff=False, realms__data=[Auditor.name])
        AssessorFactory(
            assessment=self.assessment,
            assessor_type=Assessor.TYPE_EXTERNAL,
            user=external_user,
        )
        self._test_download(self.attachment, external_user, status.HTTP_302_FOUND)

    def test_attachment_external_not_accessor(self):
        external_user = UserFactory(is_staff=False, realms__data=[Auditor.name])
        AssessorFactory(
            assessment=self.assessment,
            assessor_type=Assessor.TYPE_EXTERNAL,
        )
        self._test_download(self.attachment, external_user, status.HTTP_403_FORBIDDEN)

    def test_attachment_auditor_unrelated_staff(self):
        AssessorFactory(
            assessment=self.assessment,
            assessor_type=Assessor.TYPE_VENDOR,
            auditor_firm=self.auditor_firm,
            user=None,
        )
        self._test_download(self.attachment, self.auditor, status.HTTP_403_FORBIDDEN)

    def test_attachment_auditor_related_staff(self):
        assessor = AssessorFactory(
            assessment=self.assessment,
            assessor_type=Assessor.TYPE_VENDOR,
            auditor_firm=self.auditor_firm,
            user=None,
        )
        assessor.auditor_firm_staff.add(self.auditor)
        self._test_download(self.attachment, self.auditor, status.HTTP_302_FOUND)


class AttachmentLinkBaseTestCase(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        # clearing groups cache
        GroupWrapper.invalidate_instances()

        self.unicef_user = UserFactory(is_staff=True)
        self.attachment_link = AttachmentLinkFactory(
            attachment__file=SimpleUploadedFile(
                'simple_file.txt',
                b'these are the file contents!'
            )
        )

    def _test_delete(self, attachment_link, user, expected_status):
        response = self.forced_auth_req(
            'delete',
            reverse('attachments:link-delete', args=[attachment_link.pk]),
            user=user,
        )
        self.assertEqual(response.status_code, expected_status)
        return response


class TPMVisitAttachmentLinkTestCase(AttachmentLinkBaseTestCase):
    def setUp(self):
        super().setUp()
        self.tpm_organization = TPMPartnerFactory()
        self.tpm_staff = TPMUserFactory(tpm_partner=self.tpm_organization, is_staff=False)
        self.visit = TPMVisitFactory(tpm_partner=self.tpm_organization)
        self.attachment_link.content_object = self.visit
        self.attachment_link.save()

    def test_attachment_user_not_in_schema(self):
        another_schema_user = UserFactory(is_staff=True, realms__data=[], profile__country=None)
        self._test_delete(self.attachment_link, another_schema_user, status.HTTP_403_FORBIDDEN)

    def test_attachment_unicef(self):
        self._test_delete(self.attachment_link, self.unicef_user, status.HTTP_204_NO_CONTENT)

    def test_attachment_staff_member(self):
        self._test_delete(self.attachment_link, self.tpm_staff, status.HTTP_204_NO_CONTENT)

    def test_attachment_unrelated_staff(self):
        another_tpm_staff = TPMUserFactory(is_staff=False)
        self._test_delete(self.attachment_link, another_tpm_staff, status.HTTP_403_FORBIDDEN)

    def test_attachment_deactivated_staff(self):
        staff = TPMUserFactory(tpm_partner=self.tpm_organization, is_staff=False)
        self.visit.tpm_partner_focal_points.add(staff)
        staff.realms.update(is_active=False)
        self._test_delete(self.attachment_link, staff, status.HTTP_403_FORBIDDEN)

    def test_attachment_moved_staff(self):
        # user should have no access if not active in the organization
        #   even if it's listed in the visit and has active realm with TPM group
        tpm_organization = TPMPartnerFactory()
        staff = TPMUserFactory(tpm_partner=tpm_organization, is_staff=False)
        self.visit.tpm_partner_focal_points.add(staff)
        realm = RealmFactory(
            user=staff,
            country=self.tenant,
            organization=self.tpm_organization.organization,
            group=ThirdPartyMonitor.as_group()
        )
        realm.is_active = False
        realm.save()
        self._test_delete(self.attachment_link, staff, status.HTTP_403_FORBIDDEN)
