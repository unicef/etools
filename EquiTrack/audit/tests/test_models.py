from django.core import mail

from audit.models import Auditor, AuditorStaffMember
from audit.tests.factories import AuditPartnerFactory
from EquiTrack.tests.mixins import FastTenantTestCase
from firms.factories import UserFactory


class AuditorStaffMemberTestCase(FastTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.firm = AuditPartnerFactory()

    def test_signal(self):
        user = UserFactory()
        Auditor.invalidate_cache()

        staff_member = AuditorStaffMember.objects.create(auditor_firm=self.firm, user=user)

        self.assertIn(Auditor.name, staff_member.user.groups.values_list('name', flat=True))

        self.assertEqual(len(mail.outbox), 1)
