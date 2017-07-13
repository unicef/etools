from django.core import mail

from EquiTrack.tests.mixins import FastTenantTestCase

from .factories import AuditPartnerFactory
from ..models import AuditorStaffMember, Auditor
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
