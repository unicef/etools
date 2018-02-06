from __future__ import absolute_import, division, print_function, unicode_literals

from django.contrib.auth.models import User
from django.core import mail

from EquiTrack.tests.mixins import FastTenantTestCase
from tpm.models import ThirdPartyMonitor
from tpm.tests.factories import TPMVisitFactory, TPMPartnerFactory, TPMPartnerStaffMemberFactory


class TestTPMVisit(FastTenantTestCase):
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


class TPMStaffMemberTestCase(FastTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.firm = TPMPartnerFactory()

    def test_signal(self):
        ThirdPartyMonitor.invalidate_cache()

        staff_member = TPMPartnerStaffMemberFactory(tpm_partner=self.firm)

        self.assertIn(ThirdPartyMonitor.name, staff_member.user.groups.values_list('name', flat=True))

        self.assertEqual(len(mail.outbox), 1)

    def test_post_delete(self):
        staff_member = TPMPartnerStaffMemberFactory(tpm_partner=self.firm)
        staff_member.delete()

        user = User.objects.filter(email=staff_member.user.email).first()
        self.assertIsNotNone(user)
        self.assertEqual(user.is_active, False)
