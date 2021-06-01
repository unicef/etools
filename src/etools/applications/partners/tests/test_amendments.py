import datetime
from decimal import Decimal

from django.utils import timezone

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.amendment_utils import MergeError
from etools.applications.partners.models import Intervention, InterventionAmendment
from etools.applications.partners.permissions import PARTNERSHIP_MANAGER_GROUP, UNICEF_USER
from etools.applications.partners.tests.factories import (
    AgreementFactory,
    InterventionAmendmentFactory,
    InterventionFactory,
    InterventionResultLinkFactory,
    InterventionSupplyItemFactory,
    PartnerFactory,
    PartnerStaffFactory,
)
from etools.applications.reports.models import ResultType
from etools.applications.reports.tests.factories import (
    InterventionActivityFactory,
    LowerResultFactory,
    ReportingRequirementFactory,
    SectionFactory,
)
from etools.applications.users.tests.factories import UserFactory


class AmendmentTestCase(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        today = timezone.now().date()
        self.unicef_staff = UserFactory(is_staff=True, groups__data=[UNICEF_USER])
        self.pme = UserFactory(is_staff=True, groups__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP])

        self.partner1 = PartnerFactory(name='Partner 2')
        self.active_agreement = AgreementFactory(
            partner=self.partner1,
            status='active',
            signed_by_unicef_date=datetime.date.today(),
            signed_by_partner_date=datetime.date.today()
        )

        self.active_intervention = InterventionFactory(
            agreement=self.active_agreement,
            title='Active Intervention',
            document_type=Intervention.PD,
            start=today - datetime.timedelta(days=1),
            end=today + datetime.timedelta(days=365),
            status=Intervention.ACTIVE,
            date_sent_to_partner=today - datetime.timedelta(days=1),
            signed_by_unicef_date=today - datetime.timedelta(days=1),
            signed_by_partner_date=today - datetime.timedelta(days=1),
            unicef_signatory=self.unicef_staff,
            partner_authorized_officer_signatory=self.partner1.staff_members.all().first()
        )
        ReportingRequirementFactory(intervention=self.active_intervention)
        self.signed_pd_document = AttachmentFactory(
            code='partners_intervention_signed_pd',
            content_object=self.active_intervention,
        )

        self.result_link = InterventionResultLinkFactory(
            intervention=self.active_intervention,
            cp_output__result_type__name=ResultType.OUTPUT,
        )
        self.pd_output = LowerResultFactory(result_link=self.result_link)
        self.activity = InterventionActivityFactory(result=self.pd_output)

    def test_field_copy(self):
        amendment = InterventionAmendmentFactory(intervention=self.active_intervention)
        self.assertIsNotNone(amendment.amended_intervention)
        self.assertEqual(amendment.intervention.title, amendment.amended_intervention.title)

    def test_m2m_merge(self):
        first_section = SectionFactory()
        second_section = SectionFactory()
        third_section = SectionFactory()

        self.active_intervention.sections.add(first_section, second_section)

        amendment = InterventionAmendmentFactory(intervention=self.active_intervention)

        self.assertListEqual(
            list(amendment.amended_intervention.sections.values_list('id', flat=True)),
            [first_section.id, second_section.id],
        )

        amendment.amended_intervention.sections.remove(second_section)
        amendment.amended_intervention.sections.add(third_section)

        amendment.merge_amendment()

        self.assertListEqual(
            list(self.active_intervention.sections.values_list('id', flat=True)),
            [first_section.id, third_section.id],
        )

    def test_quarters_update(self):
        self.activity.time_frames.add(*self.active_intervention.quarters.filter(quarter__in=[1, 3]))
        amendment = InterventionAmendmentFactory(intervention=self.active_intervention)

        activity = amendment.intervention.result_links.first().ll_results.first().activities.first()
        activity_copy = amendment.amended_intervention.result_links.first().ll_results.first().activities.first()
        self.assertListEqual(list(activity_copy.time_frames.values_list('quarter', flat=True)), [1, 3])
        activity_copy.time_frames.remove(*amendment.amended_intervention.quarters.filter(quarter=1))
        activity_copy.time_frames.add(*amendment.amended_intervention.quarters.filter(quarter__in=[2, 4]))

        amendment.merge_amendment()

        self.assertListEqual(list(activity.time_frames.values_list('quarter', flat=True)), [2, 3, 4])

    def test_update_multiple_amendments(self):
        normal_amendment = InterventionAmendmentFactory(
            intervention=self.active_intervention,
            kind=InterventionAmendment.KIND_NORMAL,
        )
        contingency_amendment = InterventionAmendmentFactory(
            intervention=self.active_intervention,
            kind=InterventionAmendment.KIND_CONTINGENCY,
        )

        normal_amendment.amended_intervention.start = timezone.now().date() - datetime.timedelta(days=3)
        normal_amendment.amended_intervention.save()

        contingency_amendment.amended_intervention.end = timezone.now().date() + datetime.timedelta(days=369)
        contingency_amendment.amended_intervention.save()

        normal_amendment.merge_amendment()
        contingency_amendment.merge_amendment()

        self.active_intervention.refresh_from_db()
        self.assertEqual(self.active_intervention.start, timezone.now().date() - datetime.timedelta(days=3))
        self.assertEqual(self.active_intervention.end, timezone.now().date() + datetime.timedelta(days=369))

    def test_update_multiple_amendments_one_field(self):
        normal_amendment = InterventionAmendmentFactory(
            intervention=self.active_intervention,
            kind=InterventionAmendment.KIND_NORMAL,
        )
        contingency_amendment = InterventionAmendmentFactory(
            intervention=self.active_intervention,
            kind=InterventionAmendment.KIND_CONTINGENCY,
        )

        normal_amendment.amended_intervention.start = timezone.now().date() - datetime.timedelta(days=3)
        normal_amendment.amended_intervention.save()

        contingency_amendment.amended_intervention.start = timezone.now().date() - datetime.timedelta(days=4)
        contingency_amendment.amended_intervention.save()

        normal_amendment.merge_amendment()

        with self.assertRaises(MergeError):
            contingency_amendment.merge_amendment()

    def test_budget_calculated_fields(self):
        # since we ignore those fields during copy process, we need to make sure they will match after merge
        self.activity.unicef_cash = 2
        self.activity.cso_cash = 3
        self.activity.save()

        self.active_intervention.hq_support_cost = 7
        self.active_intervention.save()

        self.active_intervention.management_budgets.act1_unicef = 100
        self.active_intervention.management_budgets.act1_partner = 200
        self.active_intervention.management_budgets.act2_unicef = 300
        self.active_intervention.management_budgets.act2_partner = 400
        self.active_intervention.management_budgets.act3_unicef = 500
        self.active_intervention.management_budgets.act3_partner = 600
        self.active_intervention.management_budgets.save()

        self.active_intervention.planned_budget.total_hq_cash_local = 60
        self.active_intervention.planned_budget.save()

        InterventionSupplyItemFactory(intervention=self.active_intervention, unit_number=10, unit_price=3)

        amendment = InterventionAmendmentFactory(
            intervention=self.active_intervention,
            kind=InterventionAmendment.KIND_NORMAL,
        )

        budget = amendment.amended_intervention.planned_budget

        self.assertEqual(budget.partner_contribution_local, 1203)
        self.assertEqual(budget.total_unicef_cash_local_wo_hq, 902)
        self.assertEqual(budget.total_hq_cash_local, 60)
        self.assertEqual(budget.unicef_cash_local, 902 + 60)
        self.assertEqual(budget.in_kind_amount_local, 30)
        self.assertEqual(budget.in_kind_amount_local, 30)
        self.assertEqual(budget.total_local, 1203 + 902 + 60 + 30)
        self.assertEqual(
            budget.programme_effectiveness,
            ((1200 + 900) / budget.total_local * 100),
        )
        self.assertEqual(
            "{:0.2f}".format(budget.partner_contribution_percent),
            "{:0.2f}".format(1203 / (1203 + 902 + 60 + 30) * 100),
        )
        self.assertEqual(budget.total_cash_local(), 1203 + 902 + 60)
        self.assertEqual(budget.total_unicef_contribution_local(), 902 + 60 + 30)

    def test_signatures_copy(self):
        amendment = InterventionAmendmentFactory(intervention=self.active_intervention)
        amended_intervention = amendment.amended_intervention

        # signature fields are not copied
        self.assertIsNone(amended_intervention.signed_by_unicef_date)
        self.assertIsNone(amended_intervention.signed_by_partner_date)
        self.assertIsNone(amended_intervention.unicef_signatory)
        self.assertIsNone(amended_intervention.partner_authorized_officer_signatory)

        today = timezone.now().date()
        amended_intervention.signed_by_unicef_date = today
        amended_intervention.signed_by_partner_date = today
        amended_intervention.unicef_signatory = UserFactory(is_staff=True, groups__data=[UNICEF_USER])
        amended_intervention.partner_authorized_officer_signatory = PartnerStaffFactory(partner=self.partner1)
        new_signed_document = AttachmentFactory(
            code='partners_intervention_signed_pd',
            content_object=amendment.amended_intervention,
        )

        amendment.merge_amendment()

        # original signatures still untouched by merge
        self.assertNotEqual(amendment.signed_by_unicef_date, self.active_intervention.signed_by_unicef_date)
        self.assertNotEqual(amendment.signed_by_partner_date, self.active_intervention.signed_by_partner_date)
        self.assertNotEqual(amendment.unicef_signatory, self.active_intervention.unicef_signatory)
        self.assertNotEqual(amendment.partner_authorized_officer_signatory,
                            self.active_intervention.partner_authorized_officer_signatory)

        # but were moved to amendment
        self.assertEqual(amendment.signed_by_unicef_date, amended_intervention.signed_by_unicef_date)
        self.assertEqual(amendment.signed_by_partner_date, amended_intervention.signed_by_partner_date)
        self.assertEqual(amendment.unicef_signatory.id, amended_intervention.unicef_signatory_id)
        self.assertEqual(amendment.partner_authorized_officer_signatory.id,
                         amended_intervention.partner_authorized_officer_signatory_id)
        self.assertEqual(amendment.signed_amendment_attachment.first(), new_signed_document)

    def test_calculate_difference_simple_field(self):
        amendment = InterventionAmendmentFactory(
            intervention=self.active_intervention,
            kind=InterventionAmendment.KIND_NORMAL,
        )

        amendment.amended_intervention.start = timezone.now().date() - datetime.timedelta(days=3)
        amendment.amended_intervention.save()

        difference = amendment.get_difference()

        self.assertDictEqual(
            difference,
            {
                'start': {
                    'type': 'simple',
                    'diff': (self.active_intervention.start, amendment.amended_intervention.start),
                },
            },
        )

    def test_calculate_difference_one_to_one_field(self):
        amendment = InterventionAmendmentFactory(
            intervention=self.active_intervention,
            kind=InterventionAmendment.KIND_NORMAL,
        )

        amendment.amended_intervention.management_budgets.act1_unicef = 42
        amendment.amended_intervention.save()

        difference = amendment.get_difference()

        self.assertDictEqual(
            difference,
            {
                'management_budgets': {
                    'type': 'one_to_one',
                    'diff': {
                        'act1_unicef': {
                            'type': 'simple',
                            'diff': (self.active_intervention.management_budgets.act1_unicef, 42),
                        }
                    },
                },
            },
        )

    def test_calculate_difference_many_to_one_field(self):
        amendment = InterventionAmendmentFactory(
            intervention=self.active_intervention,
            kind=InterventionAmendment.KIND_NORMAL,
        )

        amendment.amended_intervention.agreement = AgreementFactory(
            partner=self.partner1,
            status='active',
            signed_by_unicef_date=datetime.date.today(),
            signed_by_partner_date=datetime.date.today()
        )
        amendment.amended_intervention.save()

        difference = amendment.get_difference()

        self.assertDictEqual(
            difference,
            {
                'agreement': {
                    'type': 'many_to_one',
                    'diff': (self.active_intervention.agreement, amendment.amended_intervention.agreement),
                },
            },
        )

    def test_calculate_difference_many_to_many_field(self):
        first_section = SectionFactory()
        second_section = SectionFactory()
        third_section = SectionFactory()

        self.active_intervention.sections.add(first_section, third_section)

        amendment = InterventionAmendmentFactory(
            intervention=self.active_intervention,
            kind=InterventionAmendment.KIND_NORMAL,
        )

        amendment.amended_intervention.sections.add(second_section)
        amendment.amended_intervention.sections.remove(third_section)

        difference = amendment.get_difference()

        self.assertDictEqual(
            difference,
            {
                'sections': {
                    'type': 'many_to_many',
                    'diff': {
                        'original': [first_section.id, third_section.id],
                        'add': [second_section.id],
                        'remove': [third_section.id],
                    },
                },
            },
        )

    def test_calculate_difference_one_to_many_field(self):
        amendment = InterventionAmendmentFactory(intervention=self.active_intervention)
        result = amendment.amended_intervention.result_links.first().ll_results.first()
        result_old_name = result.name
        result.name = 'Updated Name'
        result.save()

        difference = amendment.get_difference()
        self.assertEqual(
            difference['result_links']['diff']['update'][0]['diff']['ll_results']['diff']['update'][0]['diff']['name']['diff'][0],
            result_old_name
        )
        self.assertEqual(
            difference['result_links']['diff']['update'][0]['diff']['ll_results']['diff']['update'][0]['diff']['name']['diff'][1],
            'Updated Name'
        )

    def test_update_difference_on_merge(self):
        amendment = InterventionAmendmentFactory(
            intervention=self.active_intervention,
            kind=InterventionAmendment.KIND_NORMAL,
        )

        amendment.amended_intervention.management_budgets.act1_unicef = Decimal("42.0")
        amendment.amended_intervention.save()

        self.assertDictEqual(amendment.difference, {})
        amendment.amended_intervention.title = 'updated title'
        amendment.amended_intervention.save()

        amendment.merge_amendment()

        self.assertIn('title', amendment.difference)
        self.assertIn('management_budgets', amendment.difference)
