from django.contrib.auth import get_user_model
from django.core.management import call_command

from unicef_attachments.utils import get_denormalize_func

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.tpm.tests.factories import TPMPartnerFactory, TPMPartnerStaffMemberFactory, TPMVisitFactory


class TestTPMVisit(BaseTenantTestCase):
    def test_attachments_pv_applicable(self):
        visit = TPMVisitFactory(status='tpm_reported', tpm_activities__count=3)
        visit.tpm_activities.first().report_attachments.all().delete()

        self.assertListEqual(
            [a.pv_applicable for a in visit.tpm_activities.all()],
            [False, True, True]
        )

    def test_visit_attachments_pv_applicable(self):
        visit = TPMVisitFactory(
            status='tpm_reported',
            tpm_activities__count=3,
            report_attachments__count=1,
            report_attachments__file_type__name='overall_report',
            tpm_activities__report_attachments__count=0
        )

        self.assertListEqual(
            [a.pv_applicable for a in visit.tpm_activities.all()],
            [True, True, True]
        )


class TestTPMActivity(BaseTenantTestCase):
    def test_activity_attachment_without_intervention(self):
        visit = TPMVisitFactory(tpm_activities__count=1)
        activity = visit.tpm_activities.first()
        activity.intervention = None
        activity.save()

        attachment = AttachmentFactory(content_object=activity)
        get_denormalize_func()(attachment)


class TPMStaffMemberTestCase(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.firm = TPMPartnerFactory()
        call_command('update_notifications')

    def test_post_delete(self):
        staff_member = TPMPartnerStaffMemberFactory(
            tpm_partner=self.firm, user__profile__organization=self.firm.organization
        )
        staff_member.delete()

        user = get_user_model().objects.filter(email=staff_member.user.email).first()
        self.assertIsNotNone(user)
        self.assertEqual(user.is_active, False)
        self.assertEqual(user.profile.organization, self.firm.organization)
