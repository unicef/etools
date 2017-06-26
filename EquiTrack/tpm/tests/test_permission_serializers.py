import os
from datetime import timedelta
from unittest import skip

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.db import IntegrityError
from django.core.management import call_command

from EquiTrack.tests.mixins import FastTenantTestCase
from tpm.models import TPMVisit, ThirdPartyMonitor, UNICEFUser
from tpm.serializers.visit import TPMVisitSerializer
from tpm.tests.factories import TPMVisitFactory, TPMPartnerFactory


class TPMPermissionsBasedSerializerTestCase(FastTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tpm_partner = TPMPartnerFactory()

        cls.unicef_user = User.objects.create(username='user1', first_name='UNICEF', last_name='User')
        cls.unicef_user.groups.add(Group.objects.get_or_create(name=UNICEFUser.name)[0])

        cls.tpm_user = User.objects.create(username='user2', first_name='TPM', last_name='User')
        cls.tpm_user.groups.add(Group.objects.get_or_create(name=ThirdPartyMonitor.name)[0])

        tpm_staff_member = cls.tpm_partner.staff_members.first()
        tpm_staff_member.user = cls.tpm_user
        tpm_staff_member.save()

    def setUp(self):
        call_command('update_tpm_permissions')
        self.draft_visit = TPMVisitFactory(tpm_partner=self.tpm_partner)
        self.submitted_visit = TPMVisitFactory(tpm_partner=self.tpm_partner, status=TPMVisit.STATUSES.submitted)

    @skip("Permissions for tpm module disabled")
    def test_representation(self):
        serializer = TPMVisitSerializer(self.draft_visit, context={'user': self.unicef_user})
        self.assertDictContainsSubset({
            'status': 'draft',
            'visit_start': self.draft_visit.visit_start.isoformat(),
        }, serializer.data)
        self.assertNotIn('reject_comment', serializer.data)

        serializer = TPMVisitSerializer(self.submitted_visit, context={'user': self.unicef_user})
        self.assertDictContainsSubset({
            'status': 'submitted',
            'visit_start': self.draft_visit.visit_start.isoformat(),
        }, serializer.data)
        self.assertNotIn('reject_comment', serializer.data)

        serializer = TPMVisitSerializer(self.draft_visit, context={'user': self.tpm_user})
        self.assertDictContainsSubset({
        }, serializer.data)
        self.assertNotIn('status', serializer.data)
        self.assertNotIn('visit_start', serializer.data)
        self.assertNotIn('reject_comment', serializer.data)

        serializer = TPMVisitSerializer(self.submitted_visit, context={'user': self.tpm_user})
        self.assertDictContainsSubset({
            'status': 'submitted',
            'visit_start': self.submitted_visit.visit_start.isoformat(),
            'reject_comment': '',
        }, serializer.data)

    @skip("Permissions for tpm module disabled")
    def test_many_representation(self):
        serializer = TPMVisitSerializer(
            TPMVisit.objects.filter(id__in=[self.draft_visit.id, self.submitted_visit.id]).order_by('status'),
            many=True, context={'user': self.unicef_user})
        self.assertDictContainsSubset({
            'visit_start': self.draft_visit.visit_start.isoformat(),
            'status': 'draft',
        }, serializer.data[0])
        self.assertNotIn('reject_comment', serializer.data[0])
        self.assertDictContainsSubset({
            'visit_start': self.submitted_visit.visit_start.isoformat(),
            'status': 'submitted',
        }, serializer.data[1])
        self.assertNotIn('reject_comment', serializer.data[1])

        serializer = TPMVisitSerializer(
            TPMVisit.objects.filter(id__in=[self.draft_visit.id, self.submitted_visit.id]).order_by('status'),
            many=True, context={'user': self.tpm_user})
        self.assertNotIn('visit_start', serializer.data[0])
        self.assertNotIn('status', serializer.data[0])
        self.assertNotIn('reject_comment', serializer.data[0])
        self.assertDictContainsSubset({
            'visit_start': self.submitted_visit.visit_start.isoformat(),
            'status': 'submitted',
            'reject_comment': '',
        }, serializer.data[1])

    @skip("Permissions for tpm module disabled")
    def test_creation(self):
        serializer = TPMVisitSerializer(context={'user': self.unicef_user}, data={
            'tpm_partner': self.draft_visit.tpm_partner_id,
            'visit_start': self.draft_visit.visit_start.isoformat(),
            'visit_end': self.draft_visit.visit_end.isoformat(),
            'partnership': self.draft_visit.partnership_id,
            'results': [],
        })
        serializer.is_valid(raise_exception=True)
        visit = serializer.save()
        self.assertIsNotNone(visit.pk)
        self.assertEqual(visit.visit_start, self.draft_visit.visit_start)

        self.assertDictContainsSubset({
            'status': 'draft',
            'visit_start': self.draft_visit.visit_start.isoformat(),
        }, serializer.data)
        self.assertNotIn('reject_comment', serializer.data)

        serializer = TPMVisitSerializer(context={'user': self.tpm_user}, data={
            'tpm_partner': self.draft_visit.tpm_partner_id,
            'visit_start': self.draft_visit.visit_start.isoformat(),
            'visit_end': self.draft_visit.visit_end.isoformat(),
            'partnership': self.draft_visit.partnership_id,
            'results': [],
        })
        serializer.is_valid(raise_exception=True)
        with self.assertRaises(IntegrityError) as cm:
            serializer.save()
        self.assertIn('violates not-null constraint', cm.exception.message)

    @skip("Permissions for tpm module disabled")
    def test_updating(self):
        visit_start = self.draft_visit.visit_start
        serializer = TPMVisitSerializer(self.draft_visit, context={'user': self.unicef_user}, partial=True, data={
            'visit_start': (visit_start + timedelta(days=1)).isoformat(),
            'reject_comment': 'Test',
        })
        serializer.is_valid(raise_exception=True)
        serializer.save()
        self.assertEqual(self.draft_visit.visit_start, visit_start + timedelta(days=1))
        self.assertEqual(self.draft_visit.reject_comment, '')

        visit_start = self.submitted_visit.visit_start
        serializer = TPMVisitSerializer(self.submitted_visit, context={'user': self.unicef_user}, partial=True, data={
            'visit_start': (visit_start + timedelta(days=1)).isoformat(),
            'reject_comment': 'Test',
        })
        serializer.is_valid(raise_exception=True)
        serializer.save()
        self.assertEqual(self.submitted_visit.visit_start, visit_start)
        self.assertEqual(self.submitted_visit.reject_comment, '')

        visit_start = self.draft_visit.visit_start
        serializer = TPMVisitSerializer(self.draft_visit, context={'user': self.tpm_user}, partial=True, data={
            'visit_start': (visit_start + timedelta(days=2)).isoformat(),
            'reject_comment': 'Test2',
        })
        serializer.is_valid(raise_exception=True)
        serializer.save()
        self.assertEqual(self.draft_visit.visit_start, visit_start)
        self.assertEqual(self.draft_visit.reject_comment, '')

        visit_start = self.submitted_visit.visit_start
        serializer = TPMVisitSerializer(self.submitted_visit, context={'user': self.tpm_user}, partial=True, data={
            'visit_start': (visit_start + timedelta(days=2)).isoformat(),
            'reject_comment': 'Test2',
        })
        serializer.is_valid(raise_exception=True)
        serializer.save()
        self.assertEqual(self.submitted_visit.visit_start, visit_start)
        self.assertEqual(self.submitted_visit.reject_comment, 'Test2')
