import datetime
from decimal import Decimal

from django.utils import timezone

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.amendment_utils import INTERVENTION_AMENDMENT_RELATED_FIELDS, MergeError
from etools.applications.partners.models import (
    Intervention,
    InterventionAmendment,
    InterventionManagementBudgetItem,
    InterventionResultLink,
)
from etools.applications.partners.permissions import PARTNERSHIP_MANAGER_GROUP, UNICEF_USER
from etools.applications.partners.tests.factories import (
    AgreementFactory,
    InterventionAmendmentFactory,
    InterventionFactory,
    InterventionManagementBudgetItemFactory,
    InterventionResultLinkFactory,
    InterventionRiskFactory,
    InterventionSupplyItemFactory,
    PartnerFactory,
)
from etools.applications.reports.models import InterventionActivity, ResultType
from etools.applications.reports.tests.factories import (
    AppliedIndicatorFactory,
    InterventionActivityFactory,
    InterventionActivityItemFactory,
    LowerResultFactory,
    ReportingRequirementFactory,
    ResultFactory,
    SectionFactory,
)
from etools.applications.users.tests.factories import UserFactory


class AmendmentTestCase(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        today = timezone.now().date()
        self.unicef_staff = UserFactory(is_staff=True)
        self.pme = UserFactory(is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP])

        self.partner1 = PartnerFactory(organization=OrganizationFactory(name='Partner 2'))
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
            partner_authorized_officer_signatory=self.partner1.active_staff_members.all().first(),
            cash_transfer_modalities=[Intervention.CASH_TRANSFER_DIRECT],
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
        self.assertEqual(amendment.intervention.end, amendment.amended_intervention.end)

    def test_one_to_many_merge(self):
        first = InterventionResultLinkFactory(intervention=self.active_intervention)
        second = InterventionResultLinkFactory(intervention=self.active_intervention)

        amendment = InterventionAmendmentFactory(intervention=self.active_intervention)

        InterventionResultLink.objects.get(
            intervention=amendment.amended_intervention, cp_output=first.cp_output
        ).delete()

        second_copy = InterventionResultLink.objects.get(
            intervention=amendment.amended_intervention, cp_output=second.cp_output
        )
        second_copy.cp_output = ResultFactory()
        second_copy.save()

        third_amended = InterventionResultLinkFactory(intervention=amendment.amended_intervention)

        amendment.merge_amendment()

        # first deleted, second modified, third created
        self.assertFalse(InterventionResultLink.objects.filter(pk=first.pk).exists())
        second.refresh_from_db()
        self.assertEqual(second.cp_output, second_copy.cp_output)
        self.assertTrue(
            InterventionResultLink.objects.filter(
                intervention=self.active_intervention, cp_output=third_amended.cp_output,
            ).exists()
        )

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

        new_activity = InterventionActivityFactory(
            result__result_link=InterventionResultLinkFactory(intervention=amendment.amended_intervention),
        )
        new_activity.time_frames.add(amendment.amended_intervention.quarters.first())

        difference = amendment.get_difference()

        amendment.merge_amendment()

        self.assertListEqual(list(activity.time_frames.values_list('quarter', flat=True)), [2, 3, 4])
        self.assertEqual(
            InterventionActivity.objects.filter(
                result__result_link__intervention=amendment.intervention,
                name=new_activity.name,
            ).get().time_frames.values_list('quarter', flat=True).count(),
            1,
        )

        quarters_difference = difference['result_links']['diff']['update'][0]['diff']['ll_results']['diff']['update']
        quarters_difference = quarters_difference[0]['diff']['activities']['diff']['update'][0]['diff']['quarters']
        self.assertDictEqual(quarters_difference, {'diff': ([1, 3], [2, 3, 4]), 'type': 'simple'})

    def test_activity_items_copy(self):
        original_item = InterventionActivityItemFactory(activity=self.activity)
        amendment = InterventionAmendmentFactory(intervention=self.active_intervention)

        item = amendment.amended_intervention.result_links.first().ll_results.first().activities.first().items.first()
        self.assertIsNotNone(item)
        item.name = 'new name'
        item.save()

        amendment.difference = amendment.get_difference()
        amendment.merge_amendment()
        original_item.refresh_from_db()
        self.assertEqual(original_item.name, item.name)
        self.assertIn(
            'name',
            amendment.difference['result_links']['diff']['update'][0]['diff']['ll_results']['diff']['update'][0]
            ['diff']['activities']['diff']['update'][0]['diff']['items']['diff']['update'][0]['diff']
        )

    def test_special_amended_name(self):
        InterventionActivityItemFactory(activity=self.activity)
        amendment = InterventionAmendmentFactory(intervention=self.active_intervention)

        item = amendment.amended_intervention.result_links.first().ll_results.first().activities.first().items.first()
        item.name = 'new name'
        item.save()

        indicator = AppliedIndicatorFactory(
            lower_result=amendment.amended_intervention.result_links.first().ll_results.first(),
        )

        amendment.difference = amendment.get_difference()
        amendment.merge_amendment()

        self.assertEqual(
            self.activity.get_amended_name(),
            amendment.difference['result_links']['diff']['update'][0]['diff']['ll_results']['diff']['update'][0]
            ['diff']['activities']['diff']['update'][0]['name']
        )
        self.assertEqual(
            indicator.get_amended_name(),
            amendment.difference['result_links']['diff']['update'][0]['diff']['ll_results']['diff']['update'][0]
            ['diff']['applied_indicators']['diff']['create'][0]['name']
        )

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
            (self.active_intervention.management_budgets.unicef_total / budget.total_unicef_contribution_local() * 100),
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
        amended_intervention.unicef_signatory = UserFactory(is_staff=True)
        amended_intervention.partner_authorized_officer_signatory = UserFactory(
            realms__data=['IP Viewer'],
            profile__organization=self.active_intervention.agreement.partner.organization
        )
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

    def test_budget_items_copy(self):
        InterventionManagementBudgetItemFactory(
            budget=self.active_intervention.management_budgets, unicef_cash=0, cso_cash=42,
            kind=InterventionManagementBudgetItem.KIND_CHOICES.in_country,
        )
        self.active_intervention.management_budgets.update_cash()
        amendment = InterventionAmendmentFactory(intervention=self.active_intervention)
        self.assertEqual(amendment.amended_intervention.management_budgets.items.count(), 1)
        self.assertEqual(amendment.amended_intervention.management_budgets.act1_partner, 42)

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
                    'diff': (
                        self.active_intervention.start.strftime("%Y-%m-%d"),
                        amendment.amended_intervention.start.strftime("%Y-%m-%d")
                    ),
                },
            },
        )

    def test_calculate_difference_cash_transfer_modalities_choices(self):
        amendment = InterventionAmendmentFactory(
            intervention=self.active_intervention,
            kind=InterventionAmendment.KIND_NORMAL,
        )

        amendment.amended_intervention.cash_transfer_modalities = [Intervention.CASH_TRANSFER_PAYMENT]
        amendment.amended_intervention.save()

        difference = amendment.get_difference()

        self.assertDictEqual(
            difference,
            {
                'cash_transfer_modalities': {
                    'type': 'list[choices]',
                    'diff': (
                        [Intervention.CASH_TRANSFER_DIRECT],
                        [Intervention.CASH_TRANSFER_PAYMENT],
                    ),
                    'choices_key': 'cash_transfer_modalities',
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
                    'diff': (
                        {
                            'pk': self.active_intervention.agreement.pk,
                            'name': str(self.active_intervention.agreement),
                        }, {
                            'pk': amendment.amended_intervention.agreement.pk,
                            'name': str(amendment.amended_intervention.agreement)
                        }
                    ),
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
                        'original': [
                            {'pk': first_section.id, 'name': str(first_section)},
                            {'pk': third_section.id, 'name': str(third_section)},
                        ],
                        'add': [{'pk': second_section.id, 'name': str(second_section)}],
                        'remove': [{'pk': third_section.id, 'name': str(third_section)}],
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
            difference['result_links']['diff']['update'][0]['diff']['ll_results']['diff']['update'][0]['diff']['name'][
                'diff'][0],
            result_old_name
        )
        self.assertEqual(
            difference['result_links']['diff']['update'][0]['diff']['ll_results']['diff']['update'][0]['diff']['name'][
                'diff'][1],
            'Updated Name'
        )

    def test_calculate_difference_one_to_many_field_create(self):
        amendment = InterventionAmendmentFactory(intervention=self.active_intervention)
        new_result_link = InterventionResultLinkFactory(intervention=amendment.amended_intervention)

        difference = amendment.get_difference()
        self.assertEqual(difference['result_links']['diff']['create'][0]['pk'], new_result_link.pk)

    def test_calculate_difference_one_to_many_field_delete(self):
        amendment = InterventionAmendmentFactory(intervention=self.active_intervention)
        amendment.amended_intervention.result_links.first().delete()

        difference = amendment.get_difference()
        self.assertEqual(
            difference['result_links']['diff']['remove'][0]['pk'],
            self.active_intervention.result_links.first().pk,
        )

    def test_calculate_difference_budget_items(self):
        item = InterventionManagementBudgetItemFactory(
            budget=self.active_intervention.management_budgets, unicef_cash=0, cso_cash=42,
            kind=InterventionManagementBudgetItem.KIND_CHOICES.in_country,
        )
        self.active_intervention.management_budgets.update_cash()
        amendment = InterventionAmendmentFactory(intervention=self.active_intervention)
        item_copy = amendment.amended_intervention.management_budgets.items.first()
        item_copy.unicef_cash = 4
        item_copy.save()
        amendment.amended_intervention.management_budgets.update_cash()
        difference = amendment.get_difference()
        item_difference = difference['management_budgets']['diff']['items']['diff']['update'][0]
        self.assertEqual(item_difference['pk'], item.pk)
        self.assertEqual(item_difference['diff']['unicef_cash']['diff'], ('0.00', '4.00'))

    def test_update_difference_on_merge(self):
        amendment = InterventionAmendmentFactory(
            intervention=self.active_intervention,
            kind=InterventionAmendment.KIND_NORMAL,
        )

        amendment.amended_intervention.management_budgets.act1_unicef = Decimal("42.0")
        amendment.amended_intervention.save()

        self.assertDictEqual(amendment.difference, {})
        amendment.amended_intervention.end += datetime.timedelta(days=1)
        amendment.amended_intervention.save()

        amendment.difference = amendment.get_difference()
        amendment.merge_amendment()

        self.assertIn('end', amendment.difference)
        self.assertIn('management_budgets', amendment.difference)

    def test_update_intervention_risk(self):
        original_risk = InterventionRiskFactory(intervention=self.active_intervention)
        amendment = InterventionAmendmentFactory(
            intervention=self.active_intervention,
            kind=InterventionAmendment.KIND_NORMAL,
        )

        risk = amendment.amended_intervention.risks.get(mitigation_measures=original_risk.mitigation_measures)
        risk.mitigation_measures = "mitigation_measures"
        risk.save()

        amendment.difference = amendment.get_difference()
        amendment.merge_amendment()

        self.assertIn('risks', amendment.difference)
        original_risk.refresh_from_db()
        self.assertEqual(original_risk.mitigation_measures, risk.mitigation_measures)

    def test_update_intervention_supply_item(self):
        original_supply_item = InterventionSupplyItemFactory(intervention=self.active_intervention)
        amendment = InterventionAmendmentFactory(
            intervention=self.active_intervention,
            kind=InterventionAmendment.KIND_NORMAL,
        )

        supply_item = amendment.amended_intervention.supply_items.first()
        supply_item.title = "new title"
        supply_item.save()

        amendment.difference = amendment.get_difference()
        amendment.merge_amendment()

        self.assertIn('supply_items', amendment.difference)
        original_supply_item.refresh_from_db()
        self.assertEqual(original_supply_item.title, supply_item.title)

    def test_create_intervention_supply_item(self):
        # on amendment merge it's possible to clean extra supply items due to result links from amended intervention
        result_link = InterventionResultLinkFactory(intervention=self.active_intervention)
        original_supply_item = InterventionSupplyItemFactory(
            intervention=self.active_intervention, title='original',
            result=result_link,
        )
        supply_items_count_original = self.active_intervention.supply_items.count()
        amendment = InterventionAmendmentFactory(
            intervention=self.active_intervention,
            kind=InterventionAmendment.KIND_NORMAL,
        )
        InterventionSupplyItemFactory(intervention=amendment.amended_intervention)
        InterventionSupplyItemFactory(
            intervention=amendment.amended_intervention,
            result=InterventionResultLink.objects.get(
                intervention=amendment.amended_intervention, cp_output=result_link.cp_output
            ),
        )

        amendment.difference = amendment.get_difference()
        amendment.merge_amendment()

        self.assertIn('supply_items', amendment.difference)
        self.assertEqual(self.active_intervention.supply_items.count(), supply_items_count_original + 2)
        self.assertTrue(self.active_intervention.supply_items.filter(pk=original_supply_item.pk).exists())
        self.assertEqual(self.active_intervention.supply_items.filter(result__cp_output=result_link.cp_output).count(), 2)

    def test_update_budget_items(self):
        item = InterventionManagementBudgetItemFactory(
            budget=self.active_intervention.management_budgets, unicef_cash=0, cso_cash=42,
            kind=InterventionManagementBudgetItem.KIND_CHOICES.in_country,
        )
        self.active_intervention.management_budgets.update_cash()
        amendment = InterventionAmendmentFactory(intervention=self.active_intervention)
        item_copy = amendment.amended_intervention.management_budgets.items.first()
        item_copy.unicef_cash = Decimal(4)
        item_copy.save()
        amendment.amended_intervention.management_budgets.update_cash()

        item.refresh_from_db()
        self.assertNotEqual(item.unicef_cash, item_copy.unicef_cash)

        amendment.merge_amendment()

        item.refresh_from_db()
        self.assertEqual(item.unicef_cash, item_copy.unicef_cash)

    def test_reference_number_update(self):
        intervention = self.active_intervention
        reference_number = intervention.number
        normal_amendment = InterventionAmendmentFactory(
            intervention=self.active_intervention,
            kind=InterventionAmendment.KIND_NORMAL,
        )
        contingency_amendment = InterventionAmendmentFactory(
            intervention=self.active_intervention,
            kind=InterventionAmendment.KIND_CONTINGENCY,
        )
        self.assertEqual(
            normal_amendment.amended_intervention.number, reference_number + '-amd/1'
        )
        self.assertEqual(
            contingency_amendment.amended_intervention.number, reference_number + '-camd/1'
        )
        contingency_amendment.merge_amendment()
        intervention.refresh_from_db()
        self.assertEqual(
            intervention.number, reference_number + '-1'
        )
        contingency_amendment_1 = InterventionAmendmentFactory(
            intervention=self.active_intervention,
            kind=InterventionAmendment.KIND_CONTINGENCY,
        )
        self.assertEqual(
            contingency_amendment_1.amended_intervention.number, reference_number + '-camd/2'
        )
        contingency_amendment_1.merge_amendment()
        intervention.refresh_from_db()
        self.assertEqual(
            intervention.number, reference_number + '-2'
        )
        normal_amendment.merge_amendment()
        intervention.refresh_from_db()
        self.assertEqual(
            intervention.number, reference_number + '-3'
        )

    def test_pd_v1_no_budget_owner(self):
        self.active_intervention.budget_owner = None
        self.active_intervention.save()

        amendment = InterventionAmendmentFactory(
            intervention=self.active_intervention,
            kind=InterventionAmendment.KIND_NORMAL,
        )

        budget_owner = UserFactory()
        amendment.amended_intervention.budget_owner = budget_owner
        amendment.amended_intervention.save()

        difference = amendment.get_difference()

        self.assertDictEqual(
            difference,
            {
                'budget_owner': {
                    'type': 'many_to_one',
                    'diff': (None, {'name': str(budget_owner), 'pk': budget_owner.pk})
                }
            },
        )

        amendment.merge_amendment()
        self.active_intervention.refresh_from_db()
        self.assertEqual(self.active_intervention.budget_owner, budget_owner)

    def _check_related_fields(self, model_class, ignored_relations):
        related_fields = INTERVENTION_AMENDMENT_RELATED_FIELDS.get(model_class._meta.label, [])
        full_relations_list = related_fields + ignored_relations.get(model_class._meta.label, [])
        for field in model_class._meta.get_fields():
            field_is_simple = not (field.many_to_many or field.many_to_one or field.one_to_many or field.one_to_one)
            if field_is_simple:
                continue

            self.assertIn(
                field.name, full_relations_list,
                f'Related field {field.name} should be either presented in INTERVENTION_AMENDMENT_RELATED_FIELDS '
                f'with label {model_class._meta.label} to be copied into amendment or added to ignored fields in test'
            )
            if field.name not in related_fields:
                continue

            if field.one_to_many or field.one_to_one:
                self._check_related_fields(field.related_model, ignored_relations)

    def test_related_fields(self):
        # basically there should be reverse relations to parent model and fields you're confident about to being ignored
        ignored_fields = {
            'partners.Intervention': [
                'frs',
                'special_reporting_requirements',
                'quarters',
                'amendments',
                'amendment',
                'planned_visits',
                'reviews',
                'attachments',
                'reporting_periods',
                'activity',
                'travel_activities',
                'engagement',
                'actionpoint',
                'tpmconcern',
                'monitoring_activities',
                'country_programme',
                'unicef_signatory',
                'partner_authorized_officer_signatory',
                'prc_review_attachment',
                'signed_pd_attachment',
                'activation_letter_attachment',
                'termination_doc_attachment',
                'history',
            ],
            'reports.ReportingRequirement': ['intervention'],
            'reports.AppliedIndicator': ['lower_result'],
            # time_frames are being copied separately as quarters
            'reports.InterventionActivity': ['result', 'time_frames'],
            'reports.LowerResult': ['result_link'],
            # interventionsupplyitem is secondary relation. will be copied as partners.InterventionSupplyItem.result
            'partners.InterventionResultLink': ['intervention', 'interventionsupplyitem'],
            'partners.InterventionRisk': ['intervention'],
            'partners.InterventionSupplyItem': ['intervention'],
            'reports.InterventionActivityItem': ['activity'],
            'partners.InterventionBudget': ['intervention'],
            'partners.InterventionManagementBudget': ['intervention'],
            'partners.InterventionManagementBudgetItem': ['budget'],
        }
        self._check_related_fields(Intervention, ignored_fields)

    def test_amendment_unicef_focal_points_synchronization(self):
        focal_point_to_add = UserFactory()
        focal_point_to_keep = UserFactory()
        focal_point_to_remove = UserFactory()
        self.active_intervention.unicef_focal_points.add(focal_point_to_keep, focal_point_to_remove)
        focal_points_initial_count = self.active_intervention.unicef_focal_points.count()

        active_amendment = InterventionAmendmentFactory(
            intervention=self.active_intervention,
            kind=InterventionAmendment.KIND_NORMAL,
        )
        completed_amendment = InterventionAmendmentFactory(
            intervention=self.active_intervention,
            kind=InterventionAmendment.KIND_CONTINGENCY,
            is_active=False,
        )

        self.active_intervention.unicef_focal_points.add(focal_point_to_add)
        self.active_intervention.unicef_focal_points.remove(focal_point_to_remove)

        active_focal_points = active_amendment.amended_intervention.unicef_focal_points
        completed_focal_points = completed_amendment.amended_intervention.unicef_focal_points

        # active amendment affected, completed not
        self.assertEqual(active_focal_points.count(), focal_points_initial_count + 1 - 1)
        self.assertEqual(completed_focal_points.count(), focal_points_initial_count)
        self.assertTrue(active_focal_points.filter(pk=focal_point_to_add.pk).exists())
        self.assertFalse(active_focal_points.filter(pk=focal_point_to_remove.pk).exists())
        self.assertFalse(completed_focal_points.filter(pk=focal_point_to_add.pk).exists())
        self.assertTrue(completed_focal_points.filter(pk=focal_point_to_remove.pk).exists())

    def test_amendment_partner_focal_points_synchronization(self):
        focal_point_to_add = UserFactory(
            realms__data=['IP Viewer'],
            profile__organization=self.active_intervention.agreement.partner.organization
        )
        focal_point_to_keep = UserFactory(
            realms__data=['IP Viewer'],
            profile__organization=self.active_intervention.agreement.partner.organization
        )
        focal_point_to_remove = UserFactory(
            realms__data=['IP Viewer'],
            profile__organization=self.active_intervention.agreement.partner.organization
        )
        self.active_intervention.partner_focal_points.add(focal_point_to_keep, focal_point_to_remove)
        focal_points_initial_count = self.active_intervention.partner_focal_points.count()

        active_amendment = InterventionAmendmentFactory(
            intervention=self.active_intervention,
            kind=InterventionAmendment.KIND_NORMAL,
        )
        completed_amendment = InterventionAmendmentFactory(
            intervention=self.active_intervention,
            kind=InterventionAmendment.KIND_CONTINGENCY,
            is_active=False,
        )

        self.active_intervention.partner_focal_points.add(focal_point_to_add)
        self.active_intervention.partner_focal_points.remove(focal_point_to_remove)

        active_focal_points = active_amendment.amended_intervention.partner_focal_points
        completed_focal_points = completed_amendment.amended_intervention.partner_focal_points

        # active amendment affected, completed not
        self.assertEqual(active_focal_points.count(), focal_points_initial_count + 1 - 1)
        self.assertEqual(completed_focal_points.count(), focal_points_initial_count)
        self.assertTrue(active_focal_points.filter(pk=focal_point_to_add.pk).exists())
        self.assertFalse(active_focal_points.filter(pk=focal_point_to_remove.pk).exists())
        self.assertFalse(completed_focal_points.filter(pk=focal_point_to_add.pk).exists())
        self.assertTrue(completed_focal_points.filter(pk=focal_point_to_remove.pk).exists())

    def test_sync_budget_owner(self):
        old_budget_owner = self.active_intervention.budget_owner = UserFactory()
        self.active_intervention.save()
        active_amendment = InterventionAmendmentFactory(
            intervention=self.active_intervention,
            kind=InterventionAmendment.KIND_NORMAL,
        )
        completed_amendment = InterventionAmendmentFactory(
            intervention=self.active_intervention,
            kind=InterventionAmendment.KIND_CONTINGENCY,
            is_active=False,
        )
        self.active_intervention.budget_owner = UserFactory()
        self.active_intervention.save()

        active_amendment.amended_intervention.refresh_from_db()
        completed_amendment.amended_intervention.refresh_from_db()

        self.assertNotEqual(self.active_intervention.budget_owner, old_budget_owner)
        self.assertEqual(active_amendment.amended_intervention.budget_owner, self.active_intervention.budget_owner)
        self.assertEqual(completed_amendment.amended_intervention.budget_owner, old_budget_owner)

    def test_update_title(self):
        amendment = InterventionAmendmentFactory(
            intervention=self.active_intervention,
            kind=InterventionAmendment.KIND_NORMAL,
        )

        amendment.amended_intervention.title = '[Amended] New Title'
        amendment.amended_intervention.save()

        amendment.difference = amendment.get_difference()
        amendment.merge_amendment()

        self.assertDictEqual(
            amendment.difference,
            {
                'title': {'diff': ('Active Intervention', 'New Title'), 'type': 'simple'}
            },
        )
        self.active_intervention.refresh_from_db()
        self.assertEqual(self.active_intervention.title, 'New Title')
