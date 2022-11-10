
import datetime
import sys
from unittest import skipIf

from django.core import mail
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import connection
from django.test import SimpleTestCase

from etools.applications.audit.models import Engagement, RiskCategory
from etools.applications.audit.purchase_order.models import PurchaseOrder, PurchaseOrderItem
from etools.applications.audit.tests.factories import (
    AuditFactory,
    AuditorStaffMemberFactory,
    AuditPartnerFactory,
    DetailedFindingInfoFactory,
    EngagementFactory,
    FindingFactory,
    MicroAssessmentFactory,
    PurchaseOrderFactory,
    PurchaseOrderItemFactory,
    RiskBluePrintFactory,
    RiskCategoryFactory,
    RiskFactory,
    SpecialAuditFactory,
    SpotCheckFactory,
)
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.firms.tests.factories import BaseUserFactory
from etools.applications.users.models import Country


class EngagementStaffMemberTestCase(BaseTenantTestCase):

    @classmethod
    def setUpTestData(cls):
        call_command('update_notifications')

    def test_signal(self):
        auditor_firm = AuditPartnerFactory()
        staff_member = auditor_firm.staff_members.first()

        self.assertEqual(staff_member.user.realms.count(), 1)
        staff_member.user.realms.all().delete()
        self.assertEqual(staff_member.user.realms.count(), 0)

        engagement = EngagementFactory(staff_members=[], agreement__auditor_firm=auditor_firm)
        engagement.staff_members.add(staff_member)

        self.assertSequenceEqual(staff_member.user.profile.countries_available,
                                 [Country.objects.get(schema_name=connection.schema_name)])
        self.assertEqual(staff_member.user.profile.organization, auditor_firm.organization)
        self.assertEqual(len(mail.outbox), 1)
        mail.outbox = []


@skipIf(sys.version_info.major == 3, "This test can be deleted under Python 3")
class TestStrUnicode(SimpleTestCase):
    """
    Ensure calling str on model instances returns unicode.
    """

    def test_auditor_staff_member(self):
        user = BaseUserFactory.build(first_name='Bugs', last_name='Bunny')
        instance = AuditorStaffMemberFactory.build(user=user)
        self.assertEqual(str(instance), 'Bugs Bunny')

        user = BaseUserFactory.build(first_name='Harald', last_name='H\xe5rdr\xe5da')
        instance = AuditorStaffMemberFactory.build(user=user)
        self.assertEqual(str(instance), 'Harald H\xe5rdr\xe5da')

    def test_purchase_order(self):
        instance = PurchaseOrderFactory.build(order_number=b'two')
        self.assertEqual(str(instance), 'two')

        instance = PurchaseOrderFactory.build(order_number='tv\xe5')
        self.assertEqual(str(instance), 'tv\xe5')

    def test_engagement(self):
        purchase_order = PurchaseOrderFactory.build(order_number='two')
        instance = EngagementFactory.build(agreement=purchase_order)
        self.assertIn(' two,', str(instance))

        purchase_order = PurchaseOrderFactory.build(order_number='tv\xe5')
        instance = EngagementFactory.build(agreement=purchase_order)
        self.assertIn(' tv\xe5,', str(instance))

    def test_rick_category(self):
        instance = RiskCategoryFactory.build(header='two')
        self.assertEqual(str(instance), 'RiskCategory two')

        instance = RiskCategoryFactory.build(header='tv\xe5')
        self.assertEqual(str(instance), 'RiskCategory tv\xe5')

    def test_risk_blueprint(self):
        risk_category = RiskCategoryFactory.build(header='two')
        instance = RiskBluePrintFactory.build(category=risk_category)
        self.assertEqual(str(instance), 'RiskBluePrint at two')

        risk_category = RiskCategoryFactory.build(header='tv\xe5')
        instance = RiskBluePrintFactory.build(category=risk_category)
        self.assertEqual(str(instance), 'RiskBluePrint at tv\xe5')

    def test_risk(self):
        purchase_order = PurchaseOrderFactory.build(order_number='two')
        engagement = EngagementFactory.build(agreement=purchase_order)
        instance = RiskFactory.build(engagement=engagement)
        self.assertIn(' two,', str(instance))

        purchase_order = PurchaseOrderFactory.build(order_number='tv\xe5')
        engagement = EngagementFactory.build(agreement=purchase_order)
        instance = RiskFactory.build(engagement=engagement)
        self.assertIn(' tv\xe5,', str(instance))

    def test_spot_check(self):
        purchase_order = PurchaseOrderFactory.build(order_number='two')
        instance = SpotCheckFactory.build(agreement=purchase_order)
        self.assertIn(' two,', str(instance))

        purchase_order = PurchaseOrderFactory.build(order_number='tv\xe5')
        instance = SpotCheckFactory.build(agreement=purchase_order)
        self.assertIn(' tv\xe5,', str(instance))

    def test_finding(self):
        purchase_order = PurchaseOrderFactory.build(order_number='two')
        spot_check = SpotCheckFactory.build(agreement=purchase_order)
        instance = FindingFactory.build(spot_check=spot_check)
        self.assertIn(' two,', str(instance))

        purchase_order = PurchaseOrderFactory.build(order_number='tv\xe5')
        spot_check = SpotCheckFactory.build(agreement=purchase_order)
        instance = FindingFactory.build(spot_check=spot_check)
        self.assertIn(' tv\xe5,', str(instance))

    def test_micro_assessment(self):
        purchase_order = PurchaseOrderFactory.build(order_number='two')
        instance = MicroAssessmentFactory.build(agreement=purchase_order)
        self.assertIn(' two,', str(instance))

        purchase_order = PurchaseOrderFactory.build(order_number='tv\xe5')
        instance = MicroAssessmentFactory.build(agreement=purchase_order)
        self.assertIn(' tv\xe5,', str(instance))

    def test_detail_finding_info(self):
        purchase_order = PurchaseOrderFactory.build(order_number='two')
        micro = MicroAssessmentFactory.build(agreement=purchase_order)
        instance = DetailedFindingInfoFactory.build(micro_assesment=micro)
        self.assertIn(' two,', str(instance))

        purchase_order = PurchaseOrderFactory.build(order_number='tv\xe5')
        micro = MicroAssessmentFactory.build(agreement=purchase_order)
        instance = DetailedFindingInfoFactory.build(micro_assesment=micro)
        self.assertIn(' tv\xe5,', str(instance))

    def test_audit(self):
        purchase_order = PurchaseOrderFactory.build(order_number='two')
        instance = AuditFactory.build(agreement=purchase_order)
        self.assertIn(' two,', str(instance))

        purchase_order = PurchaseOrderFactory.build(order_number='tv\xe5')
        instance = AuditFactory.build(agreement=purchase_order)
        self.assertIn(' tv\xe5,', str(instance))

    def test_special_audit(self):
        purchase_order = PurchaseOrderFactory.build(order_number='two')
        instance = SpecialAuditFactory.build(agreement=purchase_order)
        self.assertIn(' two,', str(instance))

        purchase_order = PurchaseOrderFactory.build(order_number='tv\xe5')
        instance = SpecialAuditFactory.build(agreement=purchase_order)
        self.assertIn(' tv\xe5,', str.text_type(instance))


class TestPurchaseOrder(BaseTenantTestCase):
    def test_natural_key(self):
        po = PurchaseOrder(order_number="123")
        self.assertEqual(po.natural_key(), ("123", ))

    def test_get_by_natural_key(self):
        po = PurchaseOrderFactory(order_number="123")
        self.assertEqual(PurchaseOrder.objects.get_by_natural_key("123"), po)


class TestPurchaseOrderItem(BaseTenantTestCase):
    def test_natural_key(self):
        po = PurchaseOrderFactory(order_number="123")
        item = PurchaseOrderItem(number="321", purchase_order=po)
        self.assertEqual(item.natural_key(), (po, "321"))

    def test_get_by_natural_key(self):
        po = PurchaseOrderFactory(order_number="123")
        item = PurchaseOrderItemFactory(purchase_order=po, number="321")
        item_get = PurchaseOrderItem.objects.get_by_natural_key(po, "321")
        self.assertEqual(item_get, item)


class TestEngagement(BaseTenantTestCase):
    def test_displayed_status_partner_not_contacted(self):
        e = Engagement(status=Engagement.STATUSES.final)
        self.assertEqual(e.displayed_status, e.status)

    def test_displayed_status_comments_by_unicef(self):
        e = Engagement(
            status=Engagement.STATUSES.partner_contacted,
            date_of_comments_by_unicef=datetime.date(2001, 1, 1),
        )
        self.assertEqual(
            e.displayed_status,
            Engagement.DISPLAY_STATUSES.comments_received_by_unicef
        )

    def test_displayed_status_draft_issues_to_unicef(self):
        e = Engagement(
            status=Engagement.STATUSES.partner_contacted,
            date_of_draft_report_to_unicef=datetime.date(2001, 1, 1),
        )
        self.assertEqual(
            e.displayed_status,
            Engagement.DISPLAY_STATUSES.draft_issued_to_unicef
        )

    def test_displayed_status_comments_by_partner(self):
        e = Engagement(
            status=Engagement.STATUSES.partner_contacted,
            date_of_comments_by_ip=datetime.date(2001, 1, 1),
        )
        self.assertEqual(
            e.displayed_status,
            Engagement.DISPLAY_STATUSES.comments_received_by_partner
        )

    def test_displayed_status_draft_issues_to_partner(self):
        e = Engagement(
            status=Engagement.STATUSES.partner_contacted,
            date_of_draft_report_to_ip=datetime.date(2001, 1, 1),
        )
        self.assertEqual(
            e.displayed_status,
            Engagement.DISPLAY_STATUSES.draft_issued_to_partner
        )

    def test_displayed_status_field_visit(self):
        e = Engagement(
            status=Engagement.STATUSES.partner_contacted,
            date_of_field_visit=datetime.date(2001, 1, 1),
        )
        self.assertEqual(
            e.displayed_status,
            Engagement.DISPLAY_STATUSES.field_visit
        )

    def test_get_object_url(self):
        """Check that engagement pk is part of url"""
        engagement = EngagementFactory()
        url = engagement.get_object_url()
        self.assertIn(str(engagement.pk), url)


class TestRiskCategory(BaseTenantTestCase):
    def test_str_with_parent(self):
        parent = RiskCategoryFactory(header="Parent")
        r = RiskCategoryFactory(header="Header", parent=parent)
        self.assertEqual(str(r), "RiskCategory Header, parent: Parent")

    def test_clean_no_code(self):
        """If no code provided then validation error"""
        with self.assertRaises(ValidationError):
            r = RiskCategory()
            r.clean()

    def test_clean_code_exists(self):
        """If code exists then validation eror"""
        RiskCategoryFactory(code="123")
        with self.assertRaises(ValidationError):
            r = RiskCategory(code="123")
            r.clean()

    def test_clean(self):
        r = RiskCategory(code="123")
        self.assertIsNone(r.clean())

    def test_clean_parent(self):
        parent = RiskCategoryFactory(code="123")
        r = RiskCategory(parent=parent)
        self.assertIsNone(r.clean())

    def test_save_code_change(self):
        """If code has changed ensure tracker is updated """
        r = RiskCategoryFactory(code="123")
        r.code = "321"
        r.save()
        self.assertEqual(r.code_tracker.previous("code"), "321")
        r_updated = RiskCategory.objects.get(pk=r.pk)
        self.assertEqual(r_updated.code, "321")


class TestSpotCheck(BaseTenantTestCase):
    def test_pending_unsupported_amount(self):
        spot_check = SpotCheckFactory(
            total_amount_of_ineligible_expenditure=0,
            additional_supporting_documentation_provided=0,
            justification_provided_and_accepted=0,
            write_off_required=0
        )
        self.assertEqual(spot_check.pending_unsupported_amount, 0)


class TestAudit(BaseTenantTestCase):
    def test_pending_unsupported_amount(self):
        audit = AuditFactory(
            financial_findings=0,
            amount_refunded=0,
            additional_supporting_documentation_provided=0,
            justification_provided_and_accepted=0,
            write_off_required=0,
        )
        self.assertEqual(audit.pending_unsupported_amount, 0)
