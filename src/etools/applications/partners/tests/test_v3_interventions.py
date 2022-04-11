import datetime
import json
from decimal import Decimal
from unittest import mock, skip
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import connection
from django.test import SimpleTestCase
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APIClient
from unicef_locations.tests.factories import LocationFactory
from unicef_snapshot.utils import create_dict_with_relations, create_snapshot
from waffle.utils import get_cache

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.core.tests.factories import EmailFactory
from etools.applications.core.tests.mixins import URLAssertionMixin
from etools.applications.funds.tests.factories import FundsReservationHeaderFactory, FundsReservationItemFactory
from etools.applications.partners.models import (
    Intervention,
    InterventionManagementBudgetItem,
    InterventionReview,
    InterventionSupplyItem,
)
from etools.applications.partners.permissions import PRC_SECRETARY, UNICEF_USER
from etools.applications.partners.tests.factories import (
    AgreementFactory,
    FileTypeFactory,
    InterventionAmendmentFactory,
    InterventionAttachmentFactory,
    InterventionFactory,
    InterventionManagementBudgetItemFactory,
    InterventionResultLinkFactory,
    InterventionReviewFactory,
    InterventionSupplyItemFactory,
    PartnerFactory,
    PartnerStaffFactory,
)
from etools.applications.partners.tests.test_api_interventions import (
    BaseAPIInterventionIndicatorsCreateMixin,
    BaseAPIInterventionIndicatorsListMixin,
    BaseInterventionReportingRequirementMixin,
)
from etools.applications.reports.models import AppliedIndicator, ResultType
from etools.applications.reports.tests.factories import (
    AppliedIndicatorFactory,
    CountryProgrammeFactory,
    InterventionActivityFactory,
    LowerResultFactory,
    OfficeFactory,
    ReportingRequirementFactory,
    ResultFactory,
    SectionFactory,
)
from etools.applications.users.tests.factories import GroupFactory, UserFactory

PRP_PARTNER_SYNC = "etools.applications.partners.signals.sync_partner_to_prp"


class URLsTestCase(URLAssertionMixin, SimpleTestCase):
    """Simple test case to verify URL reversal"""

    def test_urls(self):
        """Verify URL pattern names generate the URLs we expect them to."""
        names_and_paths = (
            ('intervention-list', '', {}),
            ('intervention-detail', '1/', {'pk': 1}),
            ('intervention-accept', '1/accept/', {'pk': 1}),
            ('intervention-review', '1/review/', {'pk': 1}),
            ('intervention-send-partner', '1/send_to_partner/', {'pk': 1}),
            ('intervention-send-unicef', '1/send_to_unicef/', {'pk': 1}),
            ('intervention-budget', '1/budget/', {'intervention_pk': 1}),
            ('intervention-supply-item', '1/supply/', {'intervention_pk': 1}),
            (
                'intervention-supply-item-detail',
                '1/supply/2/',
                {'intervention_pk': 1, 'pk': 2},
            ),
            (
                'intervention-indicators-update',
                'applied-indicators/1/',
                {'pk': 1},
            ),
            (
                'intervention-reporting-requirements',
                '1/reporting-requirements/HR/',
                {'intervention_pk': 1, 'report_type': 'HR'},
            ),
            (
                'intervention-indicators-list',
                'lower-results/1/indicators/',
                {'lower_result_pk': 1},
            ),
        )
        self.assertReversal(
            names_and_paths,
            'pmp_v3:',
            '/api/pmp/v3/interventions/',
        )
        self.assertIntParamRegexes(names_and_paths, 'pmp_v3:')


class BaseInterventionTestCase(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        # explicitly set tenant - some requests switch schema to public, so subsequent ones are failing
        connection.set_tenant(self.tenant)
        self.user = UserFactory(is_staff=True, groups__data=['UNICEF User', 'Partnership Manager'])
        self.user.groups.add(GroupFactory())
        self.partner = PartnerFactory(name='Partner 1', vendor_number="VP1")
        self.agreement = AgreementFactory(
            partner=self.partner,
            signed_by_unicef_date=datetime.date.today(),
        )
        self.user_serialized = {
            "id": self.user.pk,
            "name": self.user.get_full_name(),
            "first_name": self.user.first_name,
            "middle_name": self.user.middle_name,
            "last_name": self.user.last_name,
            "username": self.user.username,
            "email": self.user.email,
            "phone": self.user.profile.phone_number,
        }


class TestList(BaseInterventionTestCase):
    def test_list_for_partner(self):
        intervention = InterventionFactory(date_sent_to_partner=None)
        user = UserFactory(is_staff=False, groups__data=[])
        user_staff_member = PartnerStaffFactory(
            partner=intervention.agreement.partner,
            user=user,
        )
        intervention.partner_focal_points.add(user_staff_member)

        # not sent to partner
        response = self.forced_auth_req(
            "get",
            reverse('pmp_v3:intervention-list'),
            user=user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        # sent to partner
        intervention.date_sent_to_partner = datetime.date.today()
        intervention.save()

        response = self.forced_auth_req(
            "get",
            reverse('pmp_v3:intervention-list'),
            user=user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], intervention.pk)

    def test_intervention_list_without_show_amendments_flag(self):
        InterventionAmendmentFactory()
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-list'),
            user=self.user,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_intervention_list_with_show_amendments_flag(self):
        InterventionAmendmentFactory()
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-list'),
            user=self.user,
            data={'show_amendments': True}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_not_authenticated(self):
        response = self.forced_auth_req(
            "get",
            reverse('pmp_v3:intervention-list'),
            user=AnonymousUser(),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_partner_user(self):
        response = self.forced_auth_req(
            "get",
            reverse('pmp_v3:intervention-list'),
            user=UserFactory(is_staff=False, groups__data=[]),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_interventions_for_empty_result_link(self):
        InterventionResultLinkFactory(cp_output=None)
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-list'),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_search_cfei_number(self):
        for _ in range(3):
            InterventionFactory()
        intervention = InterventionFactory()
        response = self.forced_auth_req(
            "get",
            reverse('pmp_v3:intervention-list'),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)

        # set cfei_number value
        cfei_number = "9723495790932423"
        intervention.cfei_number = cfei_number
        intervention.save()
        self.assertEqual(
            Intervention.objects.filter(
                cfei_number__icontains=cfei_number,
            ).count(),
            1,
        )

        response = self.forced_auth_req(
            "get",
            reverse('pmp_v3:intervention-list'),
            user=self.user,
            data={"search": cfei_number[:-5]}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_filter_editable_by_partner(self):
        InterventionFactory(unicef_court=True)
        InterventionFactory(unicef_court=False, date_sent_to_partner=None)
        for __ in range(3):
            InterventionFactory(unicef_court=False, date_sent_to_partner=timezone.now().date())

        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-list'),
            user=self.user,
            data={'editable_by': 'partner'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_filter_editable_by_unicef(self):
        InterventionFactory(unicef_court=True, date_sent_to_partner=None)
        InterventionFactory(unicef_court=False)
        for __ in range(3):
            InterventionFactory(unicef_court=True, date_sent_to_partner=timezone.now().date())

        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-list'),
            user=self.user,
            data={'editable_by': 'unicef'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)

    def test_updated_country_programmes_field_in_use(self):
        intervention = InterventionFactory()
        country_programme = CountryProgrammeFactory()
        intervention.country_programmes.add(country_programme)
        InterventionFactory()
        with self.assertNumQueries(11):
            response = self.forced_auth_req(
                "get",
                reverse('pmp_v3:intervention-list'),
                user=self.user,
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        intervention_data = sorted(response.data, key=lambda i: i['id'])[0]
        self.assertNotIn('country_programme', intervention_data)
        self.assertEqual([country_programme.id], intervention_data['country_programmes'])

    def test_intervention_list_filter_by_budget_owner(self):
        first_budget_owner = UserFactory()
        second_budget_owner = UserFactory()
        interventions = [
            InterventionFactory(budget_owner=first_budget_owner).id,
            InterventionFactory(budget_owner=second_budget_owner).id,
        ]
        InterventionFactory()
        InterventionFactory()
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-list'),
            user=self.user,
            QUERY_STRING=f'budget_owner__in={first_budget_owner.id},{second_budget_owner.id}'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertCountEqual(
            [i['id'] for i in response.data],
            interventions,
        )


class TestDetail(BaseInterventionTestCase):
    def setUp(self):
        super().setUp()
        self.intervention = InterventionFactory(unicef_signatory=self.user, date_sent_to_partner=datetime.date.today())
        frs = FundsReservationHeaderFactory(
            intervention=self.intervention,
            currency='USD',
        )
        FundsReservationItemFactory(fund_reservation=frs)
        result = ResultFactory(
            name="TestDetail",
            code="detail",
            result_type__name=ResultType.OUTPUT,
        )
        link = InterventionResultLinkFactory(
            cp_output=result,
            intervention=self.intervention,
        )
        ll = LowerResultFactory(result_link=link)
        InterventionActivityFactory(result=ll, unicef_cash=10, cso_cash=20)

    def test_get(self):
        response = self.forced_auth_req(
            "get",
            reverse('pmp_v3:intervention-detail', args=[self.intervention.pk]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data["id"], self.intervention.pk)
        self.assertEqual(data["result_links"][0]["total"], 30)
        self.assertEqual(data["unicef_signatory"], self.user_serialized)
        self.assertIn('confidential', data)

    def test_pdf(self):
        response = self.forced_auth_req(
            "get",
            reverse(
                'pmp_v3:intervention-detail-pdf',
                args=[self.intervention.pk],
            ),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_pdf_unauthenticated_user_forbidden(self):
        """Ensure an unauthenticated user gets the 403 forbidden"""
        response = APIClient().get(
            reverse(
                'pmp_v3:intervention-detail-pdf',
                args=[self.intervention.pk],
            )
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_pdf_partner_user(self):
        staff_member = PartnerStaffFactory(partner=self.intervention.agreement.partner)
        self.intervention.partner_focal_points.add(staff_member)
        response = self.forced_auth_req(
            "get",
            reverse('pmp_v3:intervention-detail-pdf', args=[self.intervention.pk]),
            user=staff_member.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_pdf_another_partner_user(self):
        staff_member = PartnerStaffFactory()
        response = self.forced_auth_req(
            "get",
            reverse('pmp_v3:intervention-detail-pdf', args=[self.intervention.pk]),
            user=staff_member.user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_pdf_not_found(self):
        response = self.forced_auth_req(
            "get",
            reverse(
                'pmp_v3:intervention-detail-pdf',
                args=[40404],
            ),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # test available actions
    def test_available_actions_unicef_review(self):
        self.intervention.date_sent_to_partner = datetime.date.today()
        self.intervention.unicef_accepted = True
        self.intervention.partner_accepted = True
        self.intervention.budget_owner = self.user
        self.intervention.save()
        InterventionReviewFactory(intervention=self.intervention, review_type='prc')

        response = self.forced_auth_req(
            "get",
            reverse('pmp_v3:intervention-detail', args=[self.intervention.pk]),
            user=self.user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("review", response.data["available_actions"])

    def test_available_actions_unicef_review_not_accepted(self):
        self.intervention.date_sent_to_partner = datetime.date.today()
        self.intervention.unicef_accepted = True
        self.intervention.partner_accepted = False
        self.intervention.budget_owner = self.user
        self.intervention.save()

        response = self.forced_auth_req(
            "get",
            reverse('pmp_v3:intervention-detail', args=[self.intervention.pk]),
            user=self.user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("review", response.data["available_actions"])

    def test_available_actions_overall_reviewer_sign(self):
        self.intervention.date_sent_to_partner = datetime.date.today()
        self.intervention.unicef_accepted = True
        self.intervention.partner_accepted = True
        self.intervention.budget_owner = self.user
        self.intervention.status = Intervention.REVIEW
        self.intervention.save()
        InterventionReviewFactory(intervention=self.intervention, review_type='prc', overall_approver=UserFactory())
        InterventionReviewFactory(intervention=self.intervention, review_type='prc', overall_approver=self.user)

        response = self.forced_auth_req(
            "get",
            reverse('pmp_v3:intervention-detail', args=[self.intervention.pk]),
            user=self.user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("sign", response.data["available_actions"])
        self.assertIn("reject_review", response.data["available_actions"])

    def test_available_actions_review_prc_secretary(self):
        self.intervention.date_sent_to_partner = datetime.date.today()
        self.intervention.unicef_accepted = True
        self.intervention.partner_accepted = True
        self.intervention.status = Intervention.REVIEW
        self.intervention.save()
        InterventionReviewFactory(intervention=self.intervention, review_type='prc', overall_approval=None)
        self.user.groups.add(GroupFactory(name=PRC_SECRETARY))

        response = self.forced_auth_req(
            "get",
            reverse('pmp_v3:intervention-detail', args=[self.intervention.pk]),
            user=self.user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("send_back_review", response.data["available_actions"])

    def test_empty_actions_while_cancelled(self):
        self.intervention.status = Intervention.CANCELLED
        self.intervention.budget_owner = self.user
        self.intervention.save()
        response = self.forced_auth_req(
            "get",
            reverse('pmp_v3:intervention-detail', args=[self.intervention.pk]),
            user=self.user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertListEqual(
            ['download_comments', 'export_results', 'export_pdf', 'export_xls'],
            response.data["available_actions"],
        )

    def test_num_queries(self):
        # clear waffle cache to avoid queries number incostintency caused by cached tenant flags
        get_cache().clear()

        [InterventionManagementBudgetItemFactory(budget=self.intervention.management_budgets) for _i in range(10)]

        # there is a lot of queries, but no duplicates caused by budget items
        with self.assertNumQueries(47):
            response = self.forced_auth_req(
                "get",
                reverse('pmp_v3:intervention-detail', args=[self.intervention.pk]),
                user=self.user
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('items', response.data['management_budgets'])


class TestCreate(BaseInterventionTestCase):
    def test_post(self):
        data = {
            "document_type": Intervention.PD,
            "title": "PMP Intervention",
            "contingency_pd": True,
            "agreement": self.agreement.pk,
            "reference_number_year": datetime.date.today().year,
            "humanitarian_flag": True,
            "cfei_number": "321",
            "budget_owner": self.user.pk,
            "phone": self.user.profile.phone_number,
            "activation_protocol": "test",
        }
        response = self.forced_auth_req(
            "post",
            reverse('pmp_v3:intervention-list'),
            user=self.user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        data = response.data
        i = Intervention.objects.get(pk=data.get("id"))
        self.assertTrue(i.humanitarian_flag)
        self.assertTrue(data.get("humanitarian_flag"))
        self.assertEqual(data.get("cfei_number"), "321")
        self.assertEqual(data.get("budget_owner"), self.user_serialized)

    def test_add_intervention_by_partner_member(self):
        partner_user = UserFactory(is_staff=False, groups__data=[])
        PartnerStaffFactory(email=partner_user.email, user=partner_user)
        response = self.forced_auth_req(
            "post",
            reverse('pmp_v3:intervention-list'),
            user=partner_user,
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_add_intervention_by_anonymous(self):
        response = self.forced_auth_req(
            "post",
            reverse('pmp_v3:intervention-list'),
            user=AnonymousUser(),
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_add_minimal_intervention(self):
        response = self.forced_auth_req(
            "post",
            reverse('pmp_v3:intervention-list'),
            user=self.user,
            data={
                'document_type': Intervention.PD,
                'title': 'My test intervention',
                'agreement': self.agreement.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_add_currency(self):
        response = self.forced_auth_req(
            "post",
            reverse('pmp_v3:intervention-list'),
            user=self.user,
            data={
                'document_type': Intervention.PD,
                'title': 'PD with Currency',
                'agreement': self.agreement.pk,
                'planned_budget': {
                    'currency': 'AFN',
                }
            }
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )
        pd = Intervention.objects.get(pk=response.data["id"])
        self.assertEqual(pd.planned_budget.currency, 'AFN')

    def test_add_currency_invalid(self):
        response = self.forced_auth_req(
            "post",
            reverse('pmp_v3:intervention-list'),
            user=self.user,
            data={
                'document_type': Intervention.PD,
                'title': 'PD with Currency',
                'agreement': self.agreement.pk,
                'planned_budget': {
                    'currency': 'WRONG',
                }
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_invalid_character_limit(self):
        data = {
            "document_type": Intervention.PD,
            "title": "PMP Intervention",
            "agreement": self.agreement.pk,
            "context": "long text" * 5000,
            "implementation_strategy": "long text" * 5000,
            "ip_program_contribution": "long text" * 5000,
        }
        response = self.forced_auth_req(
            "post",
            reverse('pmp_v3:intervention-list'),
            user=self.user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        for field_name, max_length in [
            ("context", 7000),
            ("implementation_strategy", 5000),
            ("ip_program_contribution", 5000),
        ]:
            self.assertEqual(
                response.data[field_name],
                ["This field is limited to {0} or less characters.".format(max_length)],
            )


class TestUpdate(BaseInterventionTestCase):
    def setUp(self):
        super().setUp()
        call_command("update_notifications")

    def test_patch_currency(self):
        intervention = InterventionFactory()
        intervention.unicef_focal_points.add(self.user)
        budget = intervention.planned_budget
        self.assertNotEqual(budget.currency, "PEN")

        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-detail', args=[intervention.pk]),
            user=self.user,
            data={'planned_budget': {
                "id": budget.pk,
                "currency": "PEN",
            }}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        budget.refresh_from_db()
        self.assertEqual(budget.currency, "PEN")

    def test_patch_country_programme(self):
        intervention = InterventionFactory()
        agreement = intervention.agreement
        cp = CountryProgrammeFactory()
        self.assertNotEqual(agreement.country_programme, cp)
        self.assertNotIn(cp, intervention.country_programmes.all())

        # country programme invalid, not associated with agreement
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-detail', args=[intervention.pk]),
            user=self.user,
            data={
                "country_programmes": [cp.pk],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # valid country programme
        agreement.country_programme = cp
        agreement.save()
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-detail', args=[intervention.pk]),
            user=self.user,
            data={
                "country_programmes": [cp.pk],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(cp, intervention.country_programmes.all())

    def test_update_hq_cash_local(self):
        intervention = InterventionFactory()
        intervention.unicef_focal_points.add(self.user)
        budget = intervention.planned_budget

        InterventionActivityFactory(
            result__result_link=InterventionResultLinkFactory(
                cp_output__result_type__name=ResultType.OUTPUT,
                intervention=intervention
            ),
            unicef_cash=40,
        )

        budget.refresh_from_db()
        self.assertEqual(budget.total_hq_cash_local, 0)
        self.assertEqual(budget.unicef_cash_local, 40)

        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-detail', args=[intervention.pk]),
            user=self.user,
            data={'planned_budget': {
                "id": budget.pk,
                "total_hq_cash_local": "10.00",
            }}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        budget.refresh_from_db()
        self.assertEqual(budget.total_hq_cash_local, 10)
        self.assertEqual(budget.unicef_cash_local, 50)

    def test_fields_required_on_unicef_accept(self):
        intervention = InterventionFactory(
            ip_program_contribution=None,
            status=Intervention.DRAFT,
            unicef_accepted=False,
            partner_accepted=False,
            agreement__partner=self.partner,
            date_sent_to_partner=timezone.now(),
            partner_authorized_officer_signatory=None,
            signed_by_partner_date=None,
            signed_by_unicef_date=None,
        )
        intervention.unicef_focal_points.add(self.user)
        staff_member = PartnerStaffFactory(partner=self.partner)
        intervention.partner_focal_points.add(staff_member)
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-detail', args=[intervention.pk]),
            user=self.user,
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        intervention.unicef_court = False
        intervention.save()
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-accept', args=[intervention.pk]),
            user=staff_member.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-accept', args=[intervention.pk]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn('Required fields not completed in draft', response.data[0]['description'])

        # check signature fields are not required in this case
        for field in [
            'signed_pd_attachment', 'date_sent_to_partner', 'signed_by_unicef_date',
            'signed_by_partner_date', 'partner_authorized_officer_signatory',
        ]:
            self.assertNotIn(field, response.data[0])

    def test_update_context_characters_limitation_ok(self):
        intervention = InterventionFactory(status=Intervention.DRAFT)
        intervention.unicef_focal_points.add(self.user)
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-detail', args=[intervention.pk]),
            user=self.user,
            data={'context': '*' * 7000},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_update_context_characters_limitation_fail(self):
        intervention = InterventionFactory(status=Intervention.DRAFT)
        intervention.unicef_focal_points.add(self.user)
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-detail', args=[intervention.pk]),
            user=self.user,
            data={'context': '*' * 7001},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn('context', response.data)


class TestDelete(BaseInterventionTestCase):
    def setUp(self):
        super().setUp()
        self.intervention = InterventionFactory()
        self.user = UserFactory(is_staff=True)
        self.partner_user = UserFactory(is_staff=False, groups__data=[])
        user_staff_member = PartnerStaffFactory(
            partner=self.intervention.agreement.partner,
            user=self.partner_user,
        )
        self.intervention.partner_focal_points.add(user_staff_member)
        self.intervention_qs = Intervention.objects.filter(
            pk=self.intervention.pk,
        )

    def test_with_date_sent_to_partner_reset(self):
        # attempt clear date sent, but with snapshot
        pre_save = create_dict_with_relations(self.intervention)
        self.intervention.date_sent_to_partner = None
        self.intervention.save()
        create_snapshot(self.intervention, pre_save, self.user)

        self.assertTrue(self.intervention_qs.exists())
        response = self.forced_auth_req(
            "delete",
            reverse('pmp_v3:intervention-delete', args=[self.intervention.pk]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(self.intervention_qs.exists())

    def test_delete_partner(self):
        self.assertTrue(self.intervention_qs.exists())
        response = self.forced_auth_req(
            "delete",
            reverse('pmp_v3:intervention-delete', args=[self.intervention.pk]),
            user=self.partner_user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(self.intervention_qs.exists())


class TestManagementBudget(BaseInterventionTestCase):
    def test_get(self):
        intervention = InterventionFactory()
        response = self.forced_auth_req(
            "get",
            reverse(
                "pmp_v3:intervention-budget",
                args=[intervention.pk],
            ),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertIsNotNone(intervention.management_budgets)
        self.assertEqual(data["act1_unicef"], "0.00")
        self.assertEqual(data["act1_partner"], "0.00")
        self.assertEqual(data["act1_total"], "0.00")
        self.assertEqual(data["act2_unicef"], "0.00")
        self.assertEqual(data["act2_partner"], "0.00")
        self.assertEqual(data["act2_total"], "0.00")
        self.assertEqual(data["act3_unicef"], "0.00")
        self.assertEqual(data["act3_partner"], "0.00")
        self.assertEqual(data["act3_total"], "0.00")
        self.assertEqual(data["partner_total"], "0.00")
        self.assertEqual(data["unicef_total"], "0.00")
        self.assertEqual(data["total"], "0.00")
        self.assertNotIn('intervention', response.data)

    def test_put(self):
        intervention = InterventionFactory()
        response = self.forced_auth_req(
            "put",
            reverse(
                "pmp_v3:intervention-budget",
                args=[intervention.pk],
            ),
            user=self.user,
            data={
                "act1_unicef": 1000,
                "act1_partner": 2000,
                "act2_unicef": 3000,
                "act2_partner": 4000,
                "act3_unicef": 5000,
                "act3_partner": 6000,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertIsNotNone(intervention.management_budgets)
        self.assertEqual(data["act1_unicef"], "1000.00")
        self.assertEqual(data["act1_partner"], "2000.00")
        self.assertEqual(data["act1_total"], "3000.00")
        self.assertEqual(data["act2_unicef"], "3000.00")
        self.assertEqual(data["act2_partner"], "4000.00")
        self.assertEqual(data["act2_total"], "7000.00")
        self.assertEqual(data["act3_unicef"], "5000.00")
        self.assertEqual(data["act3_partner"], "6000.00")
        self.assertEqual(data["act3_total"], "11000.00")
        self.assertEqual(data["total"], "21000.00")
        self.assertIn('intervention', response.data)

    def test_patch(self):
        intervention = InterventionFactory()
        response = self.forced_auth_req(
            "patch",
            reverse(
                "pmp_v3:intervention-budget",
                args=[intervention.pk],
            ),
            user=self.user,
            data={"act1_unicef": 1000},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data["act1_unicef"], "1000.00")
        self.assertIn('intervention', response.data)

    def test_set_cash_values_directly(self):
        intervention = InterventionFactory()
        response = self.forced_auth_req(
            'patch',
            reverse(
                "pmp_v3:intervention-budget",
                args=[intervention.pk],
            ),
            user=self.user,
            data={
                'act1_unicef': 1,
                'act1_partner': 2,
                'act2_unicef': 3,
                'act2_partner': 4,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['act1_unicef'], '1.00')
        self.assertEqual(response.data['act1_partner'], '2.00')
        self.assertEqual(response.data['act1_total'], '3.00')
        self.assertEqual(response.data['act2_unicef'], '3.00')
        self.assertEqual(response.data['act2_partner'], '4.00')
        self.assertEqual(response.data['act2_total'], '7.00')

    def test_set_cash_values_from_items(self):
        intervention = InterventionFactory()
        InterventionManagementBudgetItemFactory(budget=intervention.management_budgets, unicef_cash=8)
        response = self.forced_auth_req(
            'patch',
            reverse(
                "pmp_v3:intervention-budget",
                args=[intervention.pk],
            ),
            user=self.user,
            data={
                'act1_unicef': 1,
                'act1_partner': 2,
                'act2_unicef': 3,
                'act2_partner': 4,
                'items': [
                    {
                        'name': 'first_item', 'kind': 'operational',
                        'unit': 'item', 'no_units': '1.0', 'unit_price': '7.0',
                        'unicef_cash': '3.0', 'cso_cash': '4.0',
                    },
                    {
                        'name': 'second_item', 'kind': 'planning',
                        'unit': 'item', 'no_units': '1.0', 'unit_price': '2.0',
                        'unicef_cash': '0.0', 'cso_cash': '2.0',
                    },
                    {
                        'name': 'third_item', 'kind': 'operational',
                        'unit': 'item', 'no_units': '1.0', 'unit_price': '0.2',
                        'unicef_cash': '0.0', 'cso_cash': '0.2',
                    }
                ],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['act1_unicef'], '1.00')
        self.assertEqual(response.data['act1_partner'], '2.00')
        self.assertEqual(response.data['act2_unicef'], '3.00')
        self.assertEqual(response.data['act2_partner'], '4.20')
        self.assertEqual(response.data['act3_unicef'], '0.00')
        self.assertEqual(response.data['act3_partner'], '2.00')

    def test_set_items(self):
        intervention = InterventionFactory()
        item_to_remove = InterventionManagementBudgetItemFactory(
            budget=intervention.management_budgets,
            unicef_cash=22, cso_cash=20,
        )
        item_to_update = InterventionManagementBudgetItemFactory(
            budget=intervention.management_budgets,
            no_units=1, unit_price=42,
            unicef_cash=22, cso_cash=20,
            name='old',
        )
        self.assertEqual(intervention.management_budgets.items.count(), 2)

        response = self.forced_auth_req(
            'patch',
            reverse(
                "pmp_v3:intervention-budget",
                args=[intervention.pk],
            ),
            user=self.user,
            data={
                'items': [
                    {'id': item_to_update.id, 'name': 'new'},
                    {
                        'name': 'first_item', 'kind': 'operational',
                        'unit': 'test', 'no_units': '1.0', 'unit_price': '3.0',
                        'unicef_cash': '1.0', 'cso_cash': '2.0',
                    }
                ],
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(intervention.management_budgets.items.count(), 2)
        self.assertEqual(len(response.data['items']), 2)
        self.assertEqual(InterventionManagementBudgetItem.objects.filter(id=item_to_remove.id).exists(), False)

    def test_budget_validation(self):
        intervention = InterventionFactory()
        item_to_update = InterventionManagementBudgetItemFactory(
            budget=intervention.management_budgets,
            no_units=1, unit_price=42, unicef_cash=22, cso_cash=20,
        )

        response = self.forced_auth_req(
            'patch',
            reverse("pmp_v3:intervention-budget", args=[intervention.pk]),
            user=self.user,
            data={
                'items': [{'id': item_to_update.id, 'no_units': 2}],
            }
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn(
            'Invalid budget data. Total cash should be equal to items number * price per item.',
            response.data['items'][0]['non_field_errors'],
        )

    def test_create_items_fractional_total(self):
        intervention = InterventionFactory()

        response = self.forced_auth_req(
            'patch',
            reverse("pmp_v3:intervention-budget", args=[intervention.pk]),
            user=self.user,
            data={
                'items': [{
                    'name': 'test',
                    'kind': InterventionManagementBudgetItem.KIND_CHOICES.planning,
                    'unit': 'test',
                    'no_units': 17.9,
                    'unit_price': 14.89,
                    'unicef_cash': 4.64,
                    'cso_cash': 261.89
                }]
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)


class TestSupplyItem(BaseInterventionTestCase):
    def setUp(self):
        super().setUp()
        self.partner = PartnerFactory()
        self.intervention = InterventionFactory(date_sent_to_partner=datetime.date.today(), agreement__partner=self.partner)
        self.intervention.unicef_focal_points.add(self.user)
        self.supply_items_file = SimpleUploadedFile(
            'my_list.csv',
            u'''"Product Number","Product Title","Product Description","Unit of Measure",Quantity,"Indicative Price","Total Price"\n
            S9975020,"First aid kit A","First aid kit A",EA,1,28,28\n
            S9935097,"School-in-a-box 40 students  2016","School-in-a-box for 40 students  2016",EA,1,146.85,146.85\n
            S9935082,"Arabic Teacher's Kit","Arabic Teacher's Kit",EA,1,46.48,46.48\n
            S9935081,"Arabic Student Kit Grade 5-8","Arabic Student Kit for Grades 5 to 8.",EA,1,97.12,97.12\n
            S9903001,"AWD Kit  Periphery kit  Logistics Part","AWD Kit  Periphery kit  Logistics Part",EA,1,1059.82,1059.82\n
            ",Disclaimer : This list is not for online ordering of products but only to help staff and partners in preparing their requirements. Prices are only indicative and may vary once the final transaction is placed with UNICEF. Freight and handling charges are not included intothe price."\n
            '''.encode('utf-8'),
            content_type="multipart/form-data",
        )
        self.partner_focal_point = UserFactory(is_staff=False, groups__data=[])
        partner_focal_point_staff = PartnerStaffFactory(
            partner=self.partner, email=self.partner_focal_point.email, user=self.partner_focal_point,
        )

        self.intervention.partner_focal_points.add(partner_focal_point_staff)

    def test_list(self):
        count = 10
        for __ in range(count):
            InterventionSupplyItemFactory(intervention=self.intervention)
        for __ in range(10):
            InterventionSupplyItemFactory()
        response = self.forced_auth_req(
            "get",
            reverse(
                "pmp_v3:intervention-supply-item",
                args=[self.intervention.pk],
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), count)
        self.assertIn('id', response.data[0])

    def test_list_as_partner_user(self):
        InterventionSupplyItemFactory(intervention=self.intervention)
        response = self.forced_auth_req(
            "get",
            reverse(
                "pmp_v3:intervention-supply-item",
                args=[self.intervention.pk],
            ),
            user=self.partner_focal_point
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_post(self):
        item_qs = InterventionSupplyItem.objects.filter(
            intervention=self.intervention,
        )
        self.assertFalse(item_qs.exists())
        response = self.forced_auth_req(
            "post",
            reverse(
                "pmp_v3:intervention-supply-item",
                args=[self.intervention.pk],
            ),
            data={
                "title": "New Supply Item",
                "unit_number": 10,
                "unit_price": 2,
                "unicef_product_number": "ACME-123",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["unit_number"], "10.00")
        self.assertEqual(response.data["unit_price"], "2.00")
        self.assertEqual(response.data["total_price"], "20.00")
        self.assertEqual(response.data["unicef_product_number"], "ACME-123")
        self.assertTrue(item_qs.exists())
        item = item_qs.first()
        self.assertEqual(item.intervention, self.intervention)
        self.assertIsNone(item.result)
        self.assertEqual(item.unicef_product_number, "ACME-123")
        supply_item = InterventionSupplyItem.objects.get(id=response.data["id"])
        self.assertEqual(supply_item.provided_by, InterventionSupplyItem.PROVIDED_BY_UNICEF)

    def test_post_as_partner(self):
        self.intervention.unicef_court = False
        self.intervention.save()

        response = self.forced_auth_req(
            "post",
            reverse(
                "pmp_v3:intervention-supply-item",
                args=[self.intervention.pk],
            ),
            user=self.partner_focal_point,
            data={
                "title": "New Supply Item",
                "unit_number": 10,
                "unit_price": 2,
                "unicef_product_number": "ACME-123",
                "provided_by": "partner",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["provided_by"], "partner")
        supply_item = InterventionSupplyItem.objects.get(id=response.data["id"])
        self.assertEqual(supply_item.provided_by, InterventionSupplyItem.PROVIDED_BY_PARTNER)

    def test_post_with_cp_output(self):
        item_qs = InterventionSupplyItem.objects.filter(
            intervention=self.intervention,
        )
        result = InterventionResultLinkFactory(
            cp_output__result_type__name=ResultType.OUTPUT,
            intervention=self.intervention,
        )
        self.assertFalse(item_qs.exists())
        response = self.forced_auth_req(
            "post",
            reverse(
                "pmp_v3:intervention-supply-item",
                args=[self.intervention.pk],
            ),
            data={
                "title": "New Supply Item",
                "unit_number": 10,
                "unit_price": 2,
                "result": result.pk,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["unit_number"], "10.00")
        self.assertEqual(response.data["unit_price"], "2.00")
        self.assertEqual(response.data["total_price"], "20.00")
        self.assertTrue(item_qs.exists())
        item = item_qs.first()
        self.assertEqual(item.intervention, self.intervention)
        self.assertEqual(item.result, result)

    def test_get(self):
        item = InterventionSupplyItemFactory(
            intervention=self.intervention,
            unit_number=10,
            unit_price=2,
        )
        response = self.forced_auth_req(
            "get",
            reverse(
                "pmp_v3:intervention-supply-item-detail",
                args=[self.intervention.pk, item.pk],
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["unit_number"], "10.00")
        self.assertEqual(response.data["unit_price"], "2.00")
        self.assertEqual(response.data["total_price"], "20.00")

    def test_put(self):
        item = InterventionSupplyItemFactory(
            intervention=self.intervention,
            unit_number=10,
            unit_price=2,
        )
        response = self.forced_auth_req(
            "put",
            reverse(
                "pmp_v3:intervention-supply-item-detail",
                args=[self.intervention.pk, item.pk],
            ),
            data={
                "title": "Change Supply Item",
                "unit_number": 20,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["unit_number"], "20.00")
        self.assertEqual(response.data["unit_price"], "2.00")
        self.assertEqual(response.data["total_price"], "40.00")

    def test_patch(self):
        item = InterventionSupplyItemFactory(
            intervention=self.intervention,
            unit_number=10,
            unit_price=2,
        )
        response = self.forced_auth_req(
            "patch",
            reverse(
                "pmp_v3:intervention-supply-item-detail",
                args=[self.intervention.pk, item.pk],
            ),
            data={
                "unit_price": 3,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["unit_number"], "10.00")
        self.assertEqual(response.data["unit_price"], "3.00")
        self.assertEqual(response.data["total_price"], "30.00")

    def test_delete(self):
        item = InterventionSupplyItemFactory(intervention=self.intervention)
        response = self.forced_auth_req(
            "delete",
            reverse(
                "pmp_v3:intervention-supply-item-detail",
                args=[self.intervention.pk, item.pk],
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_as_partner_user(self):
        self.intervention.unicef_court = False
        self.intervention.save()

        item = InterventionSupplyItemFactory(intervention=self.intervention)
        response = self.forced_auth_req(
            "delete",
            reverse(
                "pmp_v3:intervention-supply-item-detail",
                args=[self.intervention.pk, item.pk],
            ),
            user=self.partner_focal_point
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_as_partner_user_unicef_court(self):
        self.intervention.unicef_court = True
        self.intervention.save()

        item = InterventionSupplyItemFactory(intervention=self.intervention)
        response = self.forced_auth_req(
            "delete",
            reverse(
                "pmp_v3:intervention-supply-item-detail",
                args=[self.intervention.pk, item.pk],
            ),
            user=self.partner_focal_point
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_budget_update_on_delete(self):
        budget = self.intervention.planned_budget
        item = InterventionSupplyItemFactory(intervention=self.intervention, unit_number=1, unit_price=2)
        self.assertEqual(budget.in_kind_amount_local, 2)
        response = self.forced_auth_req(
            "delete",
            reverse(
                "pmp_v3:intervention-supply-item-detail",
                args=[self.intervention.pk, item.pk],
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        budget.refresh_from_db()
        self.assertEqual(budget.in_kind_amount_local, 0)

    def test_upload(self):
        # add supply item that will be updated
        item = InterventionSupplyItemFactory(
            intervention=self.intervention,
            title="First aid kit A",
            unit_number=3,
            unit_price=28,
        )
        self.assertEqual(self.intervention.supply_items.count(), 1)
        response = self.forced_auth_req(
            "post",
            reverse(
                "pmp_v3:intervention-supply-item-upload",
                args=[self.intervention.pk],
            ),
            data={
                "supply_items_file": self.supply_items_file,
            },
            request_format=None,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.intervention.supply_items.count(), 5)
        # check that item unit number was updated correctly
        item.refresh_from_db()
        self.assertEqual(item.unit_number, 4)
        # check records saved correctly
        new_item = self.intervention.supply_items.get(
            unicef_product_number="S9935097",
        )
        self.assertEqual(new_item.title, "School-in-a-box 40 students  2016")
        self.assertEqual(new_item.unit_number, 1)
        self.assertEqual(new_item.unit_price, Decimal("146.85"))

    def test_upload_invalid_file(self):
        response = self.forced_auth_req(
            "post",
            reverse(
                "pmp_v3:intervention-supply-item-upload",
                args=[self.intervention.pk],
            ),
            data={
                "supply_items_file": "wrong",
            },
            request_format=None,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("supply_items_file", response.data)

    def test_upload_invalid_file_row(self):
        supply_items_file = SimpleUploadedFile(
            'my_list.csv',
            u'''"Product Number","Product Title","Product Description","Unit of Measure",Quantity,"Indicative Price","Total Price"\n
            S9975020,"First aid kit A","First aid kit A",EA,1,wrong,28\n
            '''.encode('utf-8'),
            content_type="multipart/form-data",
        )
        response = self.forced_auth_req(
            "post",
            reverse(
                "pmp_v3:intervention-supply-item-upload",
                args=[self.intervention.pk],
            ),
            data={
                "supply_items_file": supply_items_file,
            },
            request_format=None,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("supply_items_file", response.data)

    def test_upload_invalid_missing_column(self):
        supply_items_file = SimpleUploadedFile(
            'my_list.csv',
            u'''Product Number,Product Title,Quantity,Indicative Price\n
                \n
                1,test,42,\n
            '''.encode('utf-8'),
            content_type="multipart/form-data",
        )
        response = self.forced_auth_req(
            "post",
            reverse(
                "pmp_v3:intervention-supply-item-upload",
                args=[self.intervention.pk],
            ),
            data={
                "supply_items_file": supply_items_file,
            },
            request_format=None,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            'Unable to process row 3, missing value for `Indicative Price`',
            response.data["supply_items_file"]
        )


class TestInterventionUpdate(BaseInterventionTestCase):
    def _test_patch(self, mapping):
        intervention = InterventionFactory()
        intervention.unicef_focal_points.add(self.user)
        data = {}
        for field, value in mapping:
            self.assertNotEqual(getattr(intervention, field), value)
            data[field] = value
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-detail', args=[intervention.pk]),
            user=self.user,
            data=data,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        intervention.refresh_from_db()
        for field, value in mapping:
            self.assertEqual(getattr(intervention, field), value)

    def test_partner_details(self):
        intervention = InterventionFactory()
        intervention.unicef_focal_points.add(self.user)
        agreement = AgreementFactory()
        focal_1 = PartnerStaffFactory()
        focal_2 = PartnerStaffFactory()
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-detail', args=[intervention.pk]),
            user=self.user,
            data={
                "agreement": agreement.pk,
                "partner_focal_points": [focal_1.pk, focal_2.pk],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        intervention.refresh_from_db()
        self.assertEqual(intervention.agreement, agreement)
        self.assertIsNotNone(response.data['management_budgets'])
        self.assertListEqual(
            sorted([fp.pk for fp in intervention.partner_focal_points.all()]),
            sorted([focal_1.pk, focal_2.pk]),
        )

    def test_unicef_details(self):
        intervention = InterventionFactory()
        agreement = AgreementFactory()
        focal_1 = UserFactory(is_staff=True)
        focal_2 = UserFactory(is_staff=True)
        budget_owner = UserFactory(is_staff=True)
        office = OfficeFactory()
        section = SectionFactory()
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-detail', args=[intervention.pk]),
            user=self.user,
            data={
                "agreement": agreement.pk,
                "document_type": Intervention.PD,
                "unicef_focal_points": [focal_1.pk, focal_2.pk, self.user.pk],
                "budget_owner": budget_owner.pk,
                "offices": [office.pk],
                "sections": [section.pk],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        intervention.refresh_from_db()
        self.assertEqual(intervention.agreement, agreement)
        self.assertEqual(intervention.document_type, Intervention.PD)
        self.assertListEqual(list(intervention.offices.all()), [office])
        self.assertListEqual(list(intervention.sections.all()), [section])
        self.assertEqual(intervention.budget_owner, budget_owner)
        self.assertListEqual(
            sorted([i.pk for i in intervention.unicef_focal_points.all()]),
            sorted([focal_1.pk, focal_2.pk, self.user.pk]),
        )

    def test_document(self):
        mapping = (
            ("title", "Document title"),
            ("context", "Context"),
            ("implementation_strategy", "Implementation strategy"),
            ("ip_program_contribution", "Non-Contribution from partner"),
        )
        self._test_patch(mapping)

    def test_location(self):
        intervention = InterventionFactory()
        intervention.unicef_focal_points.add(self.user)
        self.assertEqual(list(intervention.flat_locations.all()), [])
        loc1 = LocationFactory()
        loc2 = LocationFactory()
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-detail', args=[intervention.pk]),
            user=self.user,
            data={
                "flat_locations": [loc1.pk, loc2.pk]
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        intervention.refresh_from_db()
        self.assertListEqual(
            list(intervention.flat_locations.all()),
            [loc1, loc2],
        )

    def test_gender(self):
        mapping = (
            ("gender_rating", Intervention.RATING_PRINCIPAL),
            ("gender_narrative", "Gender narrative"),
            ("sustainability_rating", Intervention.RATING_PRINCIPAL),
            ("sustainability_narrative", "Sustainability narrative"),
            ("equity_rating", Intervention.RATING_PRINCIPAL),
            ("equity_narrative", "Equity narrative"),
        )
        self._test_patch(mapping)

    def test_miscellaneous(self):
        mapping = (
            ("technical_guidance", "Tech guidance"),
            ("capacity_development", "Capacity dev"),
            ("other_partners_involved", "Other partners"),
            ("other_info", "Other info"),
        )
        self._test_patch(mapping)


class BaseInterventionActionTestCase(BaseInterventionTestCase):
    def setUp(self):
        super().setUp()
        call_command("update_notifications")

        self.partner_user = UserFactory(is_staff=False, groups__data=[])
        staff_member = PartnerStaffFactory(email=self.partner_user.email, user=self.partner_user)
        office = OfficeFactory()
        section = SectionFactory()

        agreement = AgreementFactory(
            partner=staff_member.partner,
            signed_by_unicef_date=datetime.date.today(),
        )
        self.intervention = InterventionFactory(
            agreement=agreement,
            start=datetime.date.today(),
            end=datetime.date.today() + datetime.timedelta(days=3),
            signed_by_unicef_date=datetime.date.today(),
            signed_by_partner_date=datetime.date.today(),
            unicef_signatory=self.user,
            partner_authorized_officer_signatory=staff_member,
            budget_owner=UserFactory(),
        )
        self.intervention.country_programmes.add(agreement.country_programme)
        self.intervention.partner_focal_points.add(staff_member)
        self.intervention.unicef_focal_points.add(self.user)
        self.intervention.offices.add(office)
        self.intervention.sections.add(section)
        AttachmentFactory(
            file="sample.pdf",
            object_id=self.intervention.pk,
            content_type=ContentType.objects.get_for_model(self.intervention),
            code="partners_intervention_signed_pd",
        )
        ReportingRequirementFactory(intervention=self.intervention)
        FundsReservationHeaderFactory(
            intervention=self.intervention,
            currency='USD',
        )

        self.notify_path = "post_office.mail.send"
        self.mock_email = EmailFactory()


class TestInterventionAccept(BaseInterventionActionTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse(
            'pmp_v3:intervention-accept',
            args=[self.intervention.pk],
        )

    def test_not_found(self):
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-accept', args=[404]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_partner_no_access(self):
        intervention = InterventionFactory()
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-accept', args=[intervention.pk]),
            user=self.partner_user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_accept(self):
        self.intervention.date_sent_to_partner = datetime.date.today()
        self.intervention.submission_date = None
        self.intervention.save()

        # unicef accepts
        self.assertFalse(self.intervention.unicef_accepted)
        mock_send = mock.Mock(return_value=self.mock_email)
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req("patch", self.url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("available_actions", response.data)
        mock_send.assert_called()
        self.intervention.refresh_from_db()
        self.assertTrue(self.intervention.unicef_accepted)
        self.assertIsNone(self.intervention.submission_date)

        # unicef attempt to accept again
        mock_send = mock.Mock()
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req("patch", self.url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("UNICEF has already accepted this PD.", response.data)
        mock_send.assert_not_called()

        # partner accepts
        self.intervention.unicef_accepted = False
        self.intervention.unicef_court = False
        self.intervention.save()

        self.assertEqual(self.intervention.status, Intervention.DRAFT)
        self.assertFalse(self.intervention.partner_accepted)
        self.assertIsNotNone(self.intervention.date_sent_to_partner)
        mock_send = mock.Mock(return_value=self.mock_email)
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req(
                "patch",
                self.url,
                user=self.partner_user,
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        mock_send.assert_called()
        self.intervention.refresh_from_db()
        self.assertTrue(self.intervention.partner_accepted)
        self.assertFalse(self.intervention.accepted_on_behalf_of_partner)
        self.assertIsNotNone(self.intervention.submission_date)

        mock_send = mock.Mock()
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req(
                "patch",
                self.url,
                user=self.partner_user,
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Partner has already accepted this PD.", response.data)
        mock_send.assert_not_called()

    def test_partner_accept_status(self):
        self.intervention.date_sent_to_partner = datetime.date.today()
        self.intervention.unicef_accepted = True
        self.intervention.unicef_court = False
        self.intervention.save()

        response = self.forced_auth_req(
            "patch",
            self.url,
            user=self.partner_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.intervention.refresh_from_db()
        self.assertEqual(self.intervention.status, Intervention.DRAFT)

    def test_accept_after_reject(self):
        self.intervention.partner_accepted = True
        self.intervention.unicef_accepted = False
        self.intervention.unicef_court = True
        self.intervention.date_sent_to_partner = timezone.now().date()
        self.intervention.save()

        result_link = InterventionResultLinkFactory(
            intervention=self.intervention,
            cp_output__result_type__name=ResultType.OUTPUT,
        )
        pd_output = LowerResultFactory(result_link=result_link)
        activity = InterventionActivityFactory(result=pd_output)
        activity.time_frames.add(self.intervention.quarters.first())

        InterventionReviewFactory(
            intervention=self.intervention, review_type='non-prc',
            overall_approver=self.user, overall_approval=False
        )
        self.assertEqual(self.intervention.reviews.count(), 1)

        response = self.forced_auth_req("patch", self.url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        self.intervention.refresh_from_db()
        self.assertTrue(self.intervention.partner_accepted)
        self.assertTrue(self.intervention.unicef_accepted)
        self.assertEqual(self.intervention.status, Intervention.DRAFT)


class TestInterventionAcceptBehalfOfPartner(BaseInterventionActionTestCase):
    def setUp(self):
        super().setUp()
        self.intervention.date_sent_to_partner = timezone.now().date()
        self.intervention.save()
        self.url = reverse(
            'pmp_v3:intervention-accept-behalf-of-partner',
            args=[self.intervention.pk],
        )

    def test_not_found(self):
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-accept-behalf-of-partner', args=[404]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_partner_no_access(self):
        response = self.forced_auth_req("patch", self.url, user=self.partner_user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Only focal points can accept", response.data)

    @patch("post_office.mail.send")
    def test_accept_on_behalf_of_partner(self, mock_email):
        mock_email.return_value = EmailFactory()

        self.intervention.unicef_accepted = True
        self.intervention.partner_accepted = False
        self.intervention.unicef_court = True
        self.intervention.save()
        self.intervention.partner_focal_points.add(*[PartnerStaffFactory(partner=self.partner) for _i in range(5)])
        self.intervention.unicef_focal_points.add(*[UserFactory(is_staff=True) for _i in range(5)])

        response = self.forced_auth_req(
            "patch",
            self.url,
            user=self.user,
            data={'submission_date': timezone.now().date() - datetime.timedelta(days=1)}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.intervention.refresh_from_db()
        self.assertEqual(mock_email.call_count, 1)
        self.assertEqual(self.intervention.partner_focal_points.count(), 6)
        self.assertEqual(self.intervention.unicef_focal_points.count(), 6)
        self.assertEqual(len(mock_email.call_args[1]['recipients']), 5 + 6)
        self.assertNotIn(self.user.email, mock_email.call_args[1]['recipients'])
        self.assertEqual(self.intervention.status, Intervention.DRAFT)
        self.assertEqual(self.intervention.unicef_court, True)
        self.assertEqual(self.intervention.partner_accepted, True)
        self.assertEqual(self.intervention.unicef_accepted, True)
        self.assertEqual(self.intervention.accepted_on_behalf_of_partner, True)

    def test_accept_partner_court(self):
        self.intervention.unicef_accepted = False
        self.intervention.partner_accepted = False
        self.intervention.unicef_court = False
        self.intervention.submission_date = None
        self.intervention.save()

        response = self.forced_auth_req(
            "patch",
            self.url,
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.intervention.refresh_from_db()
        self.assertEqual(self.intervention.status, Intervention.DRAFT)
        self.assertEqual(self.intervention.unicef_court, True)
        self.assertEqual(self.intervention.partner_accepted, True)
        self.assertEqual(self.intervention.unicef_accepted, False)
        self.assertEqual(self.intervention.submission_date, timezone.now().date())

    def test_submission_date_not_changed_if_set(self):
        self.intervention.unicef_accepted = True
        self.intervention.partner_accepted = False
        self.intervention.unicef_court = True
        self.intervention.submission_date = timezone.now().date() - datetime.timedelta(days=1)
        self.intervention.save()

        response = self.forced_auth_req(
            "patch",
            self.url,
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.intervention.refresh_from_db()
        self.assertEqual(self.intervention.submission_date, timezone.now().date() - datetime.timedelta(days=1))


class TestInterventionReview(BaseInterventionActionTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse(
            'pmp_v3:intervention-review',
            args=[self.intervention.pk],
        )

    def test_not_found(self):
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-review', args=[404]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_partner_no_access(self):
        intervention = InterventionFactory()
        response = self.forced_auth_req(
            "patch",
            reverse(
                'pmp_v3:intervention-review',
                args=[intervention.pk],
            ),
            user=self.partner_user,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_without_review_type(self):
        self.intervention.partner_accepted = True
        self.intervention.unicef_accepted = True
        self.intervention.date_sent_to_partner = datetime.date.today()
        self.intervention.save()

        response = self.forced_auth_req("patch", self.url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn("review_type", response.data)

    def test_review_validation(self):
        self.intervention.partner_accepted = True
        self.intervention.unicef_accepted = True
        self.intervention.date_sent_to_partner = datetime.date.today()
        self.intervention.save()

        response = self.forced_auth_req("patch", self.url, user=self.user, data={'review_type': 'no-review'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn('"no-review" is not a valid choice.', response.data['review_type'])

    def test_accept_required(self):
        self.intervention.partner_accepted = False
        self.intervention.unicef_accepted = False
        self.intervention.date_sent_to_partner = datetime.date.today()
        self.intervention.save()

        response = self.forced_auth_req("patch", self.url, user=self.user, data={'review_type': 'prc'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

    def test_patch(self):
        self.intervention.partner_accepted = True
        self.intervention.unicef_accepted = True
        self.intervention.date_sent_to_partner = datetime.date.today()
        self.intervention.submission_date_prc = None
        self.intervention.save()

        # unicef reviews
        mock_send = mock.Mock(return_value=self.mock_email)
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req("patch", self.url, user=self.user, data={'review_type': 'prc'})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        mock_send.assert_called()
        self.intervention.refresh_from_db()
        self.assertEqual(self.intervention.status, Intervention.REVIEW)
        self.assertEqual(self.intervention.submission_date_prc, datetime.date.today())
        review = self.intervention.reviews.last()
        self.assertEqual(review.review_type, 'prc')

        # unicef attempt to review again
        mock_send = mock.Mock()
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req("patch", self.url, user=self.user, data={'review_type': 'prc'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("PD is already in Review status.", response.data)
        mock_send.assert_not_called()

    def test_patch_after_reject(self):
        self.intervention.partner_accepted = True
        self.intervention.unicef_accepted = True
        self.intervention.date_sent_to_partner = datetime.date.today()
        self.intervention.save()
        InterventionReviewFactory(
            intervention=self.intervention, review_type='non-prc',
            overall_approver=self.user, overall_approval=False
        )
        self.assertEqual(self.intervention.reviews.count(), 1)

        # unicef reviews
        response = self.forced_auth_req("patch", self.url, user=self.user, data={'review_type': 'prc'})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.intervention.refresh_from_db()
        self.assertEqual(self.intervention.status, Intervention.REVIEW)
        self.assertEqual(self.intervention.reviews.count(), 2)
        self.assertEqual(self.intervention.review.review_type, 'prc')


class TestInterventionReviewReject(BaseInterventionActionTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse(
            'pmp_v3:intervention-reject-review',
            args=[self.intervention.pk],
        )

    def test_not_found(self):
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-review', args=[404]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_partner_no_access(self):
        response = self.forced_auth_req("patch", self.url, user=self.partner_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_not_approver(self):
        self.intervention.partner_accepted = True
        self.intervention.unicef_accepted = True
        self.intervention.date_sent_to_partner = datetime.date.today()
        self.intervention.status = Intervention.REVIEW
        self.intervention.save()
        InterventionReviewFactory(intervention=self.intervention, review_type='prc', overall_approval=None)

        response = self.forced_auth_req("patch", self.url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn('Only overall approver can reject review.', response.data)

    def test_patch(self):
        self.intervention.partner_accepted = True
        self.intervention.unicef_accepted = True
        self.intervention.date_sent_to_partner = datetime.date.today()
        self.intervention.status = Intervention.REVIEW
        self.intervention.save()
        review = InterventionReviewFactory(
            intervention=self.intervention, review_type='prc', overall_approval=None,
            overall_approver=self.user,
        )
        self.assertEqual(self.intervention.reviews.count(), 1)

        response = self.forced_auth_req("patch", self.url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(self.intervention.reviews.count(), 1)
        self.intervention.refresh_from_db()
        review.refresh_from_db()
        self.assertFalse(review.overall_approval)
        self.assertFalse(self.intervention.unicef_accepted)
        self.assertFalse(self.intervention.partner_accepted)
        self.assertEqual(self.intervention.review.review_date, timezone.now().date())


class TestInterventionReviewSendBack(BaseInterventionActionTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse(
            'pmp_v3:intervention-send-back-review',
            args=[self.intervention.pk],
        )

    def test_partner_no_access(self):
        response = self.forced_auth_req("patch", self.url, user=self.partner_user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_not_secretary(self):
        self.intervention.partner_accepted = True
        self.intervention.unicef_accepted = True
        self.intervention.date_sent_to_partner = datetime.date.today()
        self.intervention.status = Intervention.REVIEW
        self.intervention.save()
        InterventionReviewFactory(intervention=self.intervention, overall_approval=None)

        response = self.forced_auth_req("patch", self.url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_patch_comment_required(self):
        self.intervention.partner_accepted = True
        self.intervention.unicef_accepted = True
        self.intervention.date_sent_to_partner = datetime.date.today()
        self.intervention.status = Intervention.REVIEW
        self.intervention.save()
        self.user.groups.add(GroupFactory(name=PRC_SECRETARY))
        InterventionReviewFactory(intervention=self.intervention, overall_approval=None)

        response = self.forced_auth_req("patch", self.url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn('sent_back_comment', response.data)

    def test_patch(self):
        self.intervention.partner_accepted = True
        self.intervention.unicef_accepted = True
        self.intervention.date_sent_to_partner = datetime.date.today()
        self.intervention.status = Intervention.REVIEW
        self.intervention.save()
        self.user.groups.add(GroupFactory(name=PRC_SECRETARY))
        InterventionReviewFactory(intervention=self.intervention, overall_approval=None)

        mock_send = mock.Mock(return_value=self.mock_email)
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req("patch", self.url, user=self.user, data={'sent_back_comment': 'Because'})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        mock_send.assert_called()
        self.intervention.refresh_from_db()
        self.assertEqual(self.intervention.status, Intervention.DRAFT)


class TestInterventionReviews(BaseInterventionTestCase):
    def setUp(self):
        super().setUp()
        self.partner = PartnerFactory()
        self.intervention = InterventionFactory(
            date_sent_to_partner=datetime.date.today(),
            agreement__partner=self.partner,
            status=Intervention.REVIEW,
        )
        self.user.groups.add(GroupFactory(name=PRC_SECRETARY))

    def test_list(self):
        for __ in range(10):
            InterventionReviewFactory(intervention=self.intervention)

        review_qs = InterventionReview.objects.filter(
            intervention=self.intervention,
        )
        response = self.forced_auth_req(
            "get",
            reverse(
                "pmp_v3:intervention-reviews",
                args=[self.intervention.pk],
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), review_qs.count())
        self.assertIn('id', response.data[0])

    def test_post(self):
        response = self.forced_auth_req(
            "post",
            reverse(
                "pmp_v3:intervention-reviews",
                args=[self.intervention.pk],
            ),
            data={},
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_get(self):
        review = InterventionReviewFactory(intervention=self.intervention)
        response = self.forced_auth_req(
            "get",
            reverse(
                "pmp_v3:intervention-reviews-detail",
                args=[self.intervention.pk, review.pk],
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], review.pk)

    def test_patch(self):
        review = InterventionReviewFactory(
            intervention=self.intervention,
            overall_comment='first',
        )
        response = self.forced_auth_req(
            "patch",
            reverse(
                "pmp_v3:intervention-reviews-detail",
                args=[self.intervention.pk, review.pk],
            ),
            data={
                "overall_comment": "second",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], review.pk)
        self.assertEqual(response.data["overall_comment"], "second")
        review.refresh_from_db()
        self.assertEqual(review.overall_comment, "second")


class TestInterventionCancel(BaseInterventionActionTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse(
            'pmp_v3:intervention-cancel',
            args=[self.intervention.pk],
        )

    def test_not_found(self):
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-cancel', args=[404]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_partner_no_access(self):
        intervention = InterventionFactory()
        response = self.forced_auth_req(
            "patch",
            reverse(
                'pmp_v3:intervention-cancel',
                args=[intervention.pk],
            ),
            user=self.partner_user,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unicef_no_access(self):
        intervention = InterventionFactory()
        response = self.forced_auth_req(
            "patch",
            reverse(
                'pmp_v3:intervention-cancel',
                args=[intervention.pk],
            ),
            user=UserFactory(is_staff=True, groups__data=[UNICEF_USER]),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch(self):
        # unicef cancels
        self.intervention.unicef_focal_points.add(self.user)
        self.assertFalse(self.intervention.unicef_accepted)
        self.assertIsNone(self.intervention.cancel_justification)
        mock_send = mock.Mock(return_value=self.mock_email)
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req(
                "patch",
                self.url,
                data={"cancel_justification": "Needs to be cancelled"},
                user=self.user,
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send.assert_called()
        self.intervention.refresh_from_db()
        self.assertEqual(self.intervention.status, Intervention.CANCELLED)
        self.assertFalse(self.intervention.unicef_accepted)
        self.assertEqual(
            self.intervention.cancel_justification,
            "Needs to be cancelled",
        )

        # unicef attempt to cancel again
        mock_send = mock.Mock()
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req("patch", self.url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("PD has already been cancelled.", response.data)
        mock_send.assert_not_called()

    def test_invalid(self):
        mock_send = mock.Mock()
        self.intervention.status = Intervention.SUSPENDED
        self.intervention.save()

        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req("patch", self.url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        mock_send.assert_not_called()
        self.intervention.refresh_from_db()
        self.assertEqual(self.intervention.status, Intervention.SUSPENDED)


class TestInterventionTerminate(BaseInterventionActionTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse(
            'pmp_v3:intervention-terminate',
            args=[self.intervention.pk],
        )

    def test_not_found(self):
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-terminate', args=[404]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_partner_no_access(self):
        intervention = InterventionFactory()
        response = self.forced_auth_req(
            "patch",
            reverse(
                'pmp_v3:intervention-terminate',
                args=[intervention.pk],
            ),
            user=self.partner_user,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unicef_no_access(self):
        intervention = InterventionFactory()
        response = self.forced_auth_req(
            "patch",
            reverse(
                'pmp_v3:intervention-terminate',
                args=[intervention.pk],
            ),
            user=UserFactory(is_staff=True, groups__data=[UNICEF_USER]),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch(self):
        # unicef terminates
        self.assertFalse(self.intervention.unicef_accepted)
        self.intervention.unicef_focal_points.add(self.user)
        mock_send = mock.Mock(return_value=self.mock_email)
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req("patch", self.url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send.assert_called()
        self.intervention.refresh_from_db()
        self.assertEqual(self.intervention.status, Intervention.TERMINATED)
        self.assertFalse(self.intervention.unicef_accepted)

        # unicef attempt to terminate again
        mock_send = mock.Mock()
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req("patch", self.url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("PD has already been terminated.", response.data)
        mock_send.assert_not_called()


class TestInterventionSuspend(BaseInterventionActionTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse(
            'pmp_v3:intervention-suspend',
            args=[self.intervention.pk],
        )

    def test_not_found(self):
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-suspend', args=[404]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_partner_no_access(self):
        intervention = InterventionFactory()
        response = self.forced_auth_req(
            "patch",
            reverse(
                'pmp_v3:intervention-suspend',
                args=[intervention.pk],
            ),
            user=self.partner_user,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unicef_no_access(self):
        intervention = InterventionFactory()
        response = self.forced_auth_req(
            "patch",
            reverse(
                'pmp_v3:intervention-suspend',
                args=[intervention.pk],
            ),
            user=UserFactory(is_staff=True, groups__data=[UNICEF_USER]),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch(self):
        # unicef suspends
        self.intervention.date_sent_to_partner = datetime.date.today()
        self.intervention.save()
        self.intervention.unicef_focal_points.add(self.user)
        self.assertFalse(self.intervention.unicef_accepted)
        mock_send = mock.Mock(return_value=self.mock_email)
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req("patch", self.url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send.assert_called()
        self.intervention.refresh_from_db()
        self.assertEqual(self.intervention.status, Intervention.SUSPENDED)
        self.assertFalse(self.intervention.unicef_accepted)

        # unicef attempt to suspend again
        mock_send = mock.Mock()
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req("patch", self.url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("PD has already been suspended.", response.data)
        mock_send.assert_not_called()


class TestInterventionUnsuspend(BaseInterventionActionTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse(
            'pmp_v3:intervention-unsuspend',
            args=[self.intervention.pk],
        )

    def test_not_found(self):
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-unsuspend', args=[404]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_partner_no_access(self):
        intervention = InterventionFactory()
        response = self.forced_auth_req(
            "patch",
            reverse(
                'pmp_v3:intervention-unsuspend',
                args=[intervention.pk],
            ),
            user=self.partner_user,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unicef_no_access(self):
        intervention = InterventionFactory()
        response = self.forced_auth_req(
            "patch",
            reverse(
                'pmp_v3:intervention-unsuspend',
                args=[intervention.pk],
            ),
            user=UserFactory(is_staff=True, groups__data=[UNICEF_USER]),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch(self):
        # unicef unsuspends
        self.intervention.status = self.intervention.SUSPENDED
        self.intervention.date_sent_to_partner = datetime.date.today()
        self.intervention.save()
        self.intervention.management_budgets.act1_unicef = 10.00
        self.intervention.management_budgets.save()
        self.intervention.unicef_focal_points.add(self.user)
        self.assertFalse(self.intervention.unicef_accepted)
        mock_send = mock.Mock(return_value=self.mock_email)
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req("patch", self.url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send.assert_called()
        self.intervention.refresh_from_db()
        self.assertEqual(self.intervention.status, Intervention.ACTIVE)
        self.assertFalse(self.intervention.unicef_accepted)

        # unicef attempt to unsuspend again
        mock_send = mock.Mock()
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req("patch", self.url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("PD is not suspended.", response.data)
        mock_send.assert_not_called()


class TestInterventionSignature(BaseInterventionActionTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse(
            'pmp_v3:intervention-signature',
            args=[self.intervention.pk],
        )
        self.intervention.status = Intervention.REVIEW
        self.intervention.save()

    def test_not_found(self):
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-signature', args=[404]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_partner_no_access(self):
        intervention = InterventionFactory()
        response = self.forced_auth_req(
            "patch",
            reverse(
                'pmp_v3:intervention-signature',
                args=[intervention.pk],
            ),
            user=self.partner_user,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_not_approver(self):
        self.intervention.date_sent_to_partner = datetime.date.today()
        self.intervention.save()
        InterventionReviewFactory(intervention=self.intervention)
        response = self.forced_auth_req("patch", self.url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Only overall approver can accept review.', response.data)

    def test_patch(self):
        # unicef signature
        self.intervention.date_sent_to_partner = datetime.date.today()
        self.intervention.review_date_prc = None
        self.intervention.save()
        InterventionReviewFactory(
            intervention=self.intervention,
            overall_approver=self.user,
            review_type=InterventionReview.PRC,
        )
        mock_send = mock.Mock(return_value=self.mock_email)
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req("patch", self.url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        mock_send.assert_called()
        intervention = Intervention.objects.get(pk=self.intervention.pk)
        self.assertEqual(intervention.status, Intervention.SIGNATURE)
        self.assertEqual(intervention.review.review_date, timezone.now().date())
        self.assertEqual(intervention.review_date_prc, timezone.now().date())

        # unicef attempt to signature again
        mock_send = mock.Mock()
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req("patch", self.url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("PD is already in Signature status.", response.data)
        mock_send.assert_not_called()

    def test_days_from_review_to_signed(self):
        now = timezone.now().date()
        self.intervention.review_date_prc = now - datetime.timedelta(weeks=3)
        self.intervention.signed_by_partner_date = now - datetime.timedelta(weeks=2)
        self.intervention.signed_by_unicef_date = now - datetime.timedelta(weeks=1)
        self.assertEqual(self.intervention.days_from_review_to_signed, 10)


class TestInterventionUnlock(BaseInterventionActionTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse(
            'pmp_v3:intervention-unlock',
            args=[self.intervention.pk],
        )

    def test_not_found(self):
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-unlock', args=[404]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_partner_no_access(self):
        intervention = InterventionFactory()
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-unlock', args=[intervention.pk]),
            user=self.partner_user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch(self):
        self.intervention.unicef_accepted = True
        self.intervention.partner_accepted = True
        self.intervention.date_sent_to_partner = datetime.date.today()
        self.intervention.save()

        # unicef unlocks
        self.assertTrue(self.intervention.unicef_accepted)
        mock_send = mock.Mock(return_value=self.mock_email)
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req("patch", self.url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send.assert_called()
        self.intervention.refresh_from_db()
        self.assertFalse(self.intervention.unicef_accepted)

        # unicef attempt to unlock again
        mock_send = mock.Mock()
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req("patch", self.url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("PD is already unlocked.", response.data)
        mock_send.assert_not_called()

        self.intervention.unicef_accepted = True
        self.intervention.partner_accepted = True
        self.intervention.save()

        # partner unlocks
        self.assertTrue(self.intervention.partner_accepted)
        mock_send = mock.Mock(return_value=self.mock_email)
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req(
                "patch",
                self.url,
                user=self.partner_user,
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send.assert_called()
        self.intervention.refresh_from_db()
        self.assertFalse(self.intervention.partner_accepted)

        mock_send = mock.Mock()
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req(
                "patch",
                self.url,
                user=self.partner_user,
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("PD is already unlocked.", response.data)
        mock_send.assert_not_called()


class TestInterventionSendToPartner(BaseInterventionActionTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse(
            'pmp_v3:intervention-send-partner',
            args=[self.intervention.pk],
        )

    def test_not_found(self):
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-send-partner', args=[404]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_partner_no_access(self):
        intervention = InterventionFactory()
        response = self.forced_auth_req(
            "patch",
            reverse(
                'pmp_v3:intervention-send-partner',
                args=[intervention.pk],
            ),
            user=self.partner_user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unicef_no_access(self):
        intervention = InterventionFactory()
        response = self.forced_auth_req(
            "patch",
            reverse(
                'pmp_v3:intervention-send-partner',
                args=[intervention.pk],
            ),
            user=UserFactory(is_staff=True, groups__data=[UNICEF_USER]),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch(self):
        self.intervention.date_sent_to_partner = None
        self.intervention.save()
        self.assertTrue(self.intervention.unicef_court)
        self.assertIsNone(self.intervention.date_sent_to_partner)
        self.intervention.unicef_focal_points.add(self.user)
        # unicef sends PD to partner
        mock_send = mock.Mock(return_value=self.mock_email)
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req(
                "patch",
                self.url,
                user=self.user,
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send.assert_called()
        self.intervention.refresh_from_db()
        self.assertIsNotNone(self.intervention.date_sent_to_partner)
        self.assertEqual(
            response.data["date_sent_to_partner"],
            self.intervention.date_sent_to_partner.strftime("%Y-%m-%d"),
        )

        # unicef request when PD in partner court
        mock_send = mock.Mock()
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req("patch", self.url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("PD is currently with Partner", response.data)
        mock_send.assert_not_called()


class TestInterventionSendToUNICEF(BaseInterventionActionTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse(
            'pmp_v3:intervention-send-unicef',
            args=[self.intervention.pk],
        )

    def test_not_found(self):
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-send-unicef', args=[404]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_partner_no_access(self):
        partner_user = UserFactory(is_staff=False, groups__data=[])
        PartnerStaffFactory(email=partner_user.email, user=partner_user)
        response = self.forced_auth_req(
            "patch",
            self.url,
            user=partner_user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_not_focal_point_no_access(self):
        partner_user = UserFactory(is_staff=False, groups__data=[])
        PartnerStaffFactory(email=partner_user.email, user=partner_user, partner=self.partner)

        response = self.forced_auth_req(
            "patch",
            self.url,
            user=partner_user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unicef_no_access(self):
        user = UserFactory(is_staff=True, groups__data=[UNICEF_USER])
        self.intervention.unicef_focal_points.add(self.user)
        response = self.forced_auth_req(
            "patch",
            self.url,
            user=user,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_patch(self):
        self.intervention.unicef_court = False
        self.intervention.date_sent_to_partner = datetime.date.today()
        self.intervention.save()

        self.assertFalse(self.intervention.unicef_court)

        # partner sends PD to unicef
        mock_send = mock.Mock(return_value=self.mock_email)
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req(
                "patch",
                self.url,
                user=self.partner_user,
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send.assert_called()
        self.intervention.refresh_from_db()
        self.assertTrue(self.intervention.submission_date)
        self.assertEqual(
            response.data["submission_date"],
            self.intervention.submission_date.strftime("%Y-%m-%d"),
        )

        # partner request when PD in partner court
        mock_send = mock.Mock()
        with mock.patch(self.notify_path, mock_send):
            response = self.forced_auth_req(
                "patch",
                self.url,
                user=self.partner_user,
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("PD is currently with UNICEF", response.data)
        mock_send.assert_not_called()


class TestTimeframesValidation(BaseInterventionTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        call_command("update_notifications")

    def setUp(self):
        super().setUp()
        self.intervention = InterventionFactory(
            start=datetime.date(year=1970, month=1, day=1),
            end=datetime.date(year=1970, month=12, day=31),
        )
        self.intervention.unicef_focal_points.add(self.user)
        self.result_link = InterventionResultLinkFactory(
            cp_output__result_type__name=ResultType.OUTPUT,
            intervention=self.intervention
        )
        self.pd_output = LowerResultFactory(result_link=self.result_link)

        self.activity = InterventionActivityFactory(result=self.pd_output)

    def test_update_start(self):
        self.activity.time_frames.add(
            self.intervention.quarters.get(
                start_date=datetime.date(year=1970, month=4, day=1),
                end_date=datetime.date(year=1970, month=6, day=30)
            )
        )
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-detail', args=[self.intervention.pk]),
            user=self.user,
            data={'start': datetime.date(year=1970, month=5, day=1)}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['start'], '1970-05-01')

    def test_update_start_with_active_timeframe(self):
        self.activity.time_frames.add(
            self.intervention.quarters.get(
                start_date=datetime.date(year=1970, month=10, day=1),
                end_date=datetime.date(year=1970, month=12, day=31)
            )
        )
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-detail', args=[self.intervention.pk]),
            user=self.user,
            data={'start': datetime.date(year=1970, month=5, day=1)}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn('start', response.data)

    def test_update_end_with_active_timeframe(self):
        self.activity.time_frames.add(
            self.intervention.quarters.get(
                start_date=datetime.date(year=1970, month=10, day=1),
                end_date=datetime.date(year=1970, month=12, day=31)
            )
        )
        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-detail', args=[self.intervention.pk]),
            user=self.user,
            data={'end': datetime.date(year=1970, month=10, day=1)}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn('end', response.data)

    def test_shift_quarters_on_terminate_end_in_future(self):
        self.activity.time_frames.add(
            self.intervention.quarters.get(
                start_date=datetime.date(year=1970, month=10, day=1),
                end_date=datetime.date(year=1970, month=12, day=31)
            )
        )
        self.intervention.status = Intervention.ACTIVE
        self.intervention.save()
        old_quarters_num = self.intervention.quarters.count()

        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-terminate', args=[self.intervention.pk]),
            user=self.user,
            data={
                'end': datetime.date(year=1971, month=9, day=1),
                'termination_doc_attachment': AttachmentFactory(file="test_file.pdf", file_type=None, code="").id,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertGreater(self.intervention.quarters.count(), old_quarters_num)

    def test_shift_quarters_on_terminate_remove_last_quarter(self):
        self.activity.time_frames.add(
            self.intervention.quarters.get(
                start_date=datetime.date(year=1970, month=10, day=1),
                end_date=datetime.date(year=1970, month=12, day=31)
            )
        )
        self.activity.time_frames.add(
            self.intervention.quarters.get(
                start_date=datetime.date(year=1970, month=7, day=1),
                end_date=datetime.date(year=1970, month=9, day=30)
            )
        )
        self.intervention.status = Intervention.ACTIVE
        self.intervention.save()
        self.assertEqual(self.intervention.quarters.count(), 4)
        self.assertEqual(self.activity.time_frames.count(), 2)

        response = self.forced_auth_req(
            "patch",
            reverse('pmp_v3:intervention-terminate', args=[self.intervention.pk]),
            user=self.user,
            data={
                'end': datetime.date(year=1970, month=9, day=1),
                'termination_doc_attachment': AttachmentFactory(file="test_file.pdf", file_type=None, code="").id,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(self.intervention.quarters.count(), 3)
        self.assertEqual(self.activity.time_frames.count(), 1)


class TestInterventionAttachments(BaseTenantTestCase):
    def setUp(self):
        self.intervention = InterventionFactory()
        self.unicef_user = UserFactory(is_staff=True, groups__data=['UNICEF User'])
        self.partnership_manager = UserFactory(is_staff=True, groups__data=['Partnership Manager', 'UNICEF User'])
        self.example_attachment = AttachmentFactory(file="test_file.pdf", file_type=None, code="", )
        self.list_url = reverse('pmp_v3:intervention-attachment-list', args=[self.intervention.id])
        self.intervention.unicef_focal_points.add(self.partnership_manager)

    def test_list(self):
        response = self.forced_auth_req(
            'get',
            self.list_url,
            user=self.unicef_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_add_attachment(self):
        self.assertEqual(self.intervention.attachments.count(), 0)
        response = self.forced_auth_req(
            'post',
            self.list_url,
            user=self.partnership_manager,
            data={
                "type": FileTypeFactory().pk,
                "attachment_document": self.example_attachment.pk,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(self.intervention.attachments.count(), 1)
        self.assertIsInstance(response.data['intervention'], dict)

    def test_add_attachment_as_unicef_user(self):
        response = self.forced_auth_req(
            'post',
            self.list_url,
            user=self.unicef_user,
            data={},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_remove_attachment(self):
        attachment = InterventionAttachmentFactory(intervention=self.intervention)
        response = self.forced_auth_req(
            'delete',
            reverse('pmp_v3:intervention-attachments-update', args=[self.intervention.id, attachment.id]),
            user=self.partnership_manager,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class TestPMPInterventionIndicatorsUpdateView(BaseTenantTestCase):
    def setUp(self):
        self.intervention = InterventionFactory()
        self.result_link = InterventionResultLinkFactory(
            cp_output__result_type__name=ResultType.OUTPUT,
            intervention=self.intervention,
        )
        self.lower_result = LowerResultFactory(result_link=self.result_link)
        # Create another result link/lower result pair that will break this
        # test if the views don't behave properly
        LowerResultFactory(result_link=InterventionResultLinkFactory(
            cp_output__result_type__name=ResultType.OUTPUT,
        ))
        self.indicator = AppliedIndicatorFactory(
            lower_result=self.lower_result,
        )
        self.url = reverse(
            'pmp_v3:intervention-indicators-update',
            args=[self.indicator.pk]
        )

        location = LocationFactory()
        self.section = SectionFactory()

        self.result_link.intervention.flat_locations.add(location)
        self.result_link.intervention.sections.add(self.section)
        self.user = UserFactory()
        self.partnership_manager = UserFactory(
            is_staff=True,
            groups__data=['Partnership Manager', 'UNICEF User'],
        )
        self.intervention.unicef_focal_points.add(self.partnership_manager)

    def test_permission(self):
        response = self.forced_auth_req(
            'patch',
            self.url,
            user=self.user,
            data={},
        )
        self.assertEquals(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch(self):
        data = {
            "is_active": False,
            "is_high_frequency": True,
        }
        self.assertTrue(self.indicator.is_active)
        self.assertFalse(self.indicator.is_high_frequency)
        self.assertEqual(self.intervention.status, Intervention.DRAFT)
        response = self.forced_auth_req(
            'patch',
            self.url,
            user=self.partnership_manager,
            data=data,
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        # The id of the newly-created indicator should be associated with
        # lower result, and it should be the only one associated with that
        # result.
        self.assertEqual(
            [response.data['id']],
            [
                indicator.pk for indicator
                in self.lower_result.applied_indicators.all()
            ]
        )
        self.assertFalse(response.data["is_active"])
        self.assertTrue(response.data["is_high_frequency"])
        self.indicator.refresh_from_db()
        self.assertFalse(self.indicator.is_active)

    def test_update_indicator_title(self):
        old_title = self.indicator.indicator.title
        old_code = self.indicator.indicator.code
        response = self.forced_auth_req(
            'patch',
            self.url,
            user=self.partnership_manager,
            data={'indicator': {'title': f'new_{old_title}', 'code': 'new_code'}},
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK, response.data)
        self.assertNotEqual(response.data['id'], self.indicator.id)
        self.assertNotEqual(response.data['indicator']['id'], self.indicator.indicator.id)
        self.assertEqual(response.data['indicator']['title'], f'new_{old_title}')
        self.assertEqual(response.data['indicator']['code'], old_code)
        self.assertFalse(AppliedIndicator.objects.filter(id=self.indicator.id).exists())

    def test_update_indicator_title_intervention_was_signed(self):
        intervention = self.indicator.lower_result.result_link.intervention

        pre_save = create_dict_with_relations(intervention)

        intervention.status = Intervention.SIGNED
        intervention.save()

        create_snapshot(intervention, pre_save, self.partnership_manager)

        intervention.status = Intervention.DRAFT
        intervention.save()

        response = self.forced_auth_req(
            'patch',
            self.url,
            user=self.partnership_manager,
            data={'indicator': {'title': 'new title'}},
        )
        self.assertEquals(response.status_code, status.HTTP_200_OK, response.data)
        self.assertNotEqual(response.data['id'], self.indicator.id)
        self.assertNotEqual(response.data['indicator']['id'], self.indicator.indicator.id)
        self.assertEqual(response.data['indicator']['title'], 'new title')
        self.assertTrue(AppliedIndicator.objects.filter(id=self.indicator.id).exists())
        self.assertFalse(AppliedIndicator.objects.get(id=self.indicator.id).is_active)


class TestPMPInterventionReportingRequirementView(
        BaseInterventionReportingRequirementMixin,
        BaseTenantTestCase,
):
    def _get_url(self, report_type, intervention=None):
        intervention = self.intervention if intervention is None else intervention
        return reverse(
            "pmp_v3:intervention-reporting-requirements",
            args=[intervention.pk, report_type]
        )


class TestPMPInterventionIndicatorsListView(
        BaseAPIInterventionIndicatorsListMixin,
        BaseTenantTestCase,
):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.url = reverse(
            'pmp_v3:intervention-indicators-list',
            kwargs={'lower_result_pk': cls.lower_result.pk},
        )

    @skip("waiting of permissions")
    def test_no_permission_user_forbidden(self):
        super().test_no_permission_user_forbidden()

    @skip("waiting of permissions")
    def test_group_permission(self):
        super().test_group_permission()


class TestPMPInterventionIndicatorsCreateView(
        BaseAPIInterventionIndicatorsCreateMixin,
        BaseTenantTestCase,
):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.result_link.cp_output.result_type.name = ResultType.OUTPUT
        cls.result_link.cp_output.result_type.save()
        cls.url = reverse(
            'pmp_v3:intervention-indicators-list',
            kwargs={'lower_result_pk': cls.lower_result.pk},
        )

    def test_target_baseline_validation(self):
        """
        """
        user = UserFactory(is_staff=True)
        self.lower_result.result_link.intervention.unicef_focal_points.add(user)
        data = self.data.copy()
        # valid values
        data.update({
            'indicator': {'title': 'Indicator test title '},
            'target': {'v': '3.2', 'd': 1},
            'baseline': {'v': '7.2', 'd': 1},
        })
        response = self._make_request(user, data)
        self.assertResponseFundamentals(response)

        # invalid values
        _target_baseline_error_cases = {
            "3,2": "Invalid format. Use '.' (dot) instead of ',' (comma) for decimal values.",
            "string value": "Invalid number"
        }
        for i, (value, response_error) in enumerate(_target_baseline_error_cases.items()):
            data.update({
                'indicator': {'title': f'Indicator test title {i}'},
                'target': {'v': value, 'd': 1},
                'baseline': {'v': value, 'd': 1}
            })
            response = self._make_request(user, data)
            self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
            response_json = json.loads(response.rendered_content)
            self.assertEqual(response_json['target'], [response_error])
            self.assertEqual(response_json['baseline'], [response_error])
