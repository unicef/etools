from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import sys
from unittest import skipIf, TestCase

from django.core import mail

from EquiTrack.tests.mixins import FastTenantTestCase

from .factories import (
    AuditPartnerFactory,
    AuditorStaffMemberFactory,
    EngagementFactory,
    PurchaseOrderFactory,
    RiskBluePrintFactory,
    RiskCategoryFactory,
    RiskFactory,
    SpotCheckFactory,
    )
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


@skipIf(sys.version_info.major == 3, "This test can be deleted under Python 3")
class TestStrUnicode(TestCase):
    '''Ensure calling str() on model instances returns UTF8-encoded text and unicode() returns unicode.'''
    def test_auditor_staff_member(self):
        user = UserFactory.build(first_name='Bugs', last_name='Bunny')
        instance = AuditorStaffMemberFactory.build(user=user)
        self.assertEqual(str(instance), b'Bugs Bunny')
        self.assertEqual(unicode(instance), 'Bugs Bunny')

        user = UserFactory.build(first_name='Harald', last_name='H\xe5rdr\xe5da')
        instance = AuditorStaffMemberFactory.build(user=user)
        self.assertEqual(str(instance), b'Harald H\xc3\xa5rdr\xc3\xa5da')
        self.assertEqual(unicode(instance), 'Harald H\xe5rdr\xe5da')

    def test_purchase_order(self):
        instance = PurchaseOrderFactory.build(order_number=b'two')
        self.assertEqual(str(instance), b'two')
        self.assertEqual(unicode(instance), 'two')

        instance = PurchaseOrderFactory.build(order_number='tv\xe5')
        self.assertEqual(str(instance), b'tv\xc3\xa5')
        self.assertEqual(unicode(instance), 'tv\xe5')

    def test_engagement(self):
        purchase_order = PurchaseOrderFactory.build(order_number='two')
        instance = EngagementFactory.build(agreement=purchase_order)
        self.assertIn(b' two,', str(instance))
        self.assertIn(' two,', unicode(instance))

        purchase_order = PurchaseOrderFactory.build(order_number='tv\xe5')
        instance = EngagementFactory.build(agreement=purchase_order)
        self.assertIn(b' tv\xc3\xa5,', str(instance))
        self.assertIn(' tv\xe5,', unicode(instance))

    def test_rick_category(self):
        instance = RiskCategoryFactory.build(header='two')
        self.assertEqual(str(instance), b'RiskCategory two')
        self.assertEqual(unicode(instance), 'RiskCategory two')

        instance = RiskCategoryFactory.build(header='tv\xe5')
        self.assertEqual(str(instance), b'RiskCategory tv\xc3\xa5')
        self.assertEqual(unicode(instance), 'RiskCategory tv\xe5')

    def test_risk_blueprint(self):
        risk_category = RiskCategoryFactory.build(header='two')
        instance = RiskBluePrintFactory.build(category=risk_category)
        self.assertEqual(str(instance), b'RiskBluePrint at two')
        self.assertEqual(unicode(instance), 'RiskBluePrint at two')

        risk_category = RiskCategoryFactory.build(header='tv\xe5')
        instance = RiskBluePrintFactory.build(category=risk_category)
        self.assertEqual(str(instance), b'RiskBluePrint at tv\xc3\xa5')
        self.assertEqual(unicode(instance), 'RiskBluePrint at tv\xe5')

    def test_risk(self):
        purchase_order = PurchaseOrderFactory.build(order_number='two')
        engagement = EngagementFactory.build(agreement=purchase_order)
        instance = RiskFactory.build(engagement=engagement)
        self.assertIn(b' two,', str(instance))
        self.assertIn(' two,', unicode(instance))

        purchase_order = PurchaseOrderFactory.build(order_number='tv\xe5')
        engagement = EngagementFactory.build(agreement=purchase_order)
        instance = RiskFactory.build(engagement=engagement)
        self.assertIn(b' tv\xc3\xa5,', str(instance))
        self.assertIn(' tv\xe5,', unicode(instance))

    def test_spot_check(self):
        purchase_order = PurchaseOrderFactory.build(order_number='two')
        instance = SpotCheckFactory.build(agreement=purchase_order)
        self.assertIn(b' two,', str(instance))
        self.assertIn(' two,', unicode(instance))

        purchase_order = PurchaseOrderFactory.build(order_number='tv\xe5')
        instance = SpotCheckFactory.build(agreement=purchase_order)
        self.assertIn(b' tv\xc3\xa5,', str(instance))
        self.assertIn(' tv\xe5,', unicode(instance))

    def test_finding(self):
        purchase_order = PurchaseOrderFactory.build(order_number='two')
        instance = SpotCheckFactory.build(agreement=purchase_order)
        self.assertIn(b' two,', str(instance))
        self.assertIn(' two,', unicode(instance))

        purchase_order = PurchaseOrderFactory.build(order_number='tv\xe5')
        instance = SpotCheckFactory.build(agreement=purchase_order)
        self.assertIn(b' tv\xc3\xa5,', str(instance))
        self.assertIn(' tv\xe5,', unicode(instance))
