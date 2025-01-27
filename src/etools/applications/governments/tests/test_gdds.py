import datetime
from unittest import skip

from django.contrib.auth.models import AnonymousUser
from django.db import connection
from django.urls import reverse
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APIClient
from unicef_locations.tests.factories import LocationFactory
from waffle.utils import get_cache

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.funds.models import FundsReservationHeader
from etools.applications.funds.tests.factories import FundsReservationHeaderFactory, FundsReservationItemFactory
from etools.applications.governments.models import GDD, GDDSupplyItem
from etools.applications.governments.permissions import PARTNERSHIP_MANAGER_GROUP, PRC_SECRETARY, UNICEF_USER
from etools.applications.governments.tests.factories import (
    EWPActivityFactory,
    EWPOutputFactory,
    GDDActivityFactory,
    GDDAmendmentFactory,
    GDDFactory,
    GDDKeyInterventionFactory,
    GDDResultLinkFactory,
    GDDReviewFactory,
    GDDSupplyItemFactory,
    GovernmentEWPFactory,
)
from etools.applications.organizations.models import OrganizationType
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.reports.models import ResultType
from etools.applications.reports.tests.factories import CountryProgrammeFactory, SectionFactory
from etools.applications.users.tests.factories import CountryFactory, GroupFactory, RealmFactory, UserFactory


class BaseGDDTestCase(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        # explicitly set tenant - some requests switch schema to public, so subsequent ones are failing
        connection.set_tenant(self.tenant)
        self.unicef_user = UserFactory(
            is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]
        )
        self.partner = PartnerFactory(
            organization=OrganizationFactory(
                name='Partner 1', vendor_number="VP1", organization_type=OrganizationType.GOVERNMENT)
        )
        self.user_serialized = {
            "id": self.unicef_user.pk,
            "name": self.unicef_user.get_full_name(),
            "first_name": self.unicef_user.first_name,
            "middle_name": self.unicef_user.middle_name,
            "last_name": self.unicef_user.last_name,
            "username": self.unicef_user.email,
            "email": self.unicef_user.email,
            "phone": '',
        }


class TestList(BaseGDDTestCase):
    def test_list_for_partner(self):
        gdd = GDDFactory(partner=self.partner, date_sent_to_partner=None)
        staff_member = UserFactory(
            realms__data=['IP Viewer'],
            profile__organization=gdd.partner.organization,
        )
        gdd.partner_focal_points.add(staff_member)

        # not sent to partner
        with self.assertNumQueries(8):
            response = self.forced_auth_req(
                "get",
                reverse('governments:gdd-list'),
                user=staff_member,
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        # sent to partner
        gdd.date_sent_to_partner = datetime.date.today()
        gdd.save()

        response = self.forced_auth_req(
            "get",
            reverse('governments:gdd-list'),
            user=staff_member,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], gdd.pk)

    def test_intervention_list_without_show_amendments_flag(self):
        GDDAmendmentFactory()
        with self.assertNumQueries(9):
            response = self.forced_auth_req(
                'get',
                reverse('governments:gdd-list'),
                user=self.unicef_user,
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_intervention_list_with_show_amendments_flag(self):
        for i in range(20):
            GDDAmendmentFactory()

        with self.assertNumQueries(9):
            response = self.forced_auth_req(
                'get',
                reverse('governments:gdd-list'),
                user=self.unicef_user,
                data={'show_amendments': True}
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 40)

    def test_intervention_list_with_pagination(self):
        for i in range(30):
            GDDFactory()

        with self.assertNumQueries(10):
            response = self.forced_auth_req(
                'get',
                reverse('governments:gdd-list'),
                user=self.unicef_user,
                data={'page_size': 20, 'page': 1}
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 20)

    def test_not_authenticated(self):
        response = self.forced_auth_req(
            "get",
            reverse('governments:gdd-list'),
            user=AnonymousUser(),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_not_partner_user(self):
        response = self.forced_auth_req(
            "get",
            reverse('governments:gdd-list'),
            user=UserFactory(is_staff=False, realms__data=[]),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # def test_list_interventions_for_empty_result_link(self):
    #     GDDResultLinkFactory(cp_output=None)
    #     response = self.forced_auth_req(
    #         'get',
    #         reverse('governments:gdd-list'),
    #         user=self.unicef_user,
    #     )
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_search_cfei_number(self):
        for _ in range(3):
            GDDFactory()
        gdd = GDDFactory()
        response = self.forced_auth_req(
            "get",
            reverse('governments:gdd-list'),
            user=self.unicef_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)

        # set cfei_number value
        cfei_number = "9723495790932423"
        gdd.cfei_number = cfei_number
        gdd.save()
        self.assertEqual(
            GDD.objects.filter(
                cfei_number__icontains=cfei_number,
            ).count(),
            1,
        )

        response = self.forced_auth_req(
            "get",
            reverse('governments:gdd-list'),
            user=self.unicef_user,
            data={"search": cfei_number[:-5]}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_filter_editable_by_partner(self):
        GDDFactory(unicef_court=True)
        GDDFactory(unicef_court=False, date_sent_to_partner=None)
        for __ in range(3):
            GDDFactory(unicef_court=False, date_sent_to_partner=timezone.now().date())

        response = self.forced_auth_req(
            'get',
            reverse('governments:gdd-list'),
            user=self.unicef_user,
            data={'editable_by': 'partner'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_filter_editable_by_unicef(self):
        GDDFactory(unicef_court=True, date_sent_to_partner=None)
        GDDFactory(unicef_court=False)
        for __ in range(3):
            GDDFactory(unicef_court=True, date_sent_to_partner=timezone.now().date())

        response = self.forced_auth_req(
            'get',
            reverse('governments:gdd-list'),
            user=self.unicef_user,
            data={'editable_by': 'unicef'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)

    def test_updated_country_programmes_field_in_use(self):
        gdd = GDDFactory()
        country_programme = CountryProgrammeFactory()
        gdd.country_programme = country_programme
        gdd.save()
        GDDFactory()
        with self.assertNumQueries(9):
            response = self.forced_auth_req(
                "get",
                reverse('governments:gdd-list'),
                user=self.unicef_user,
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        intervention_data = sorted(response.data, key=lambda i: i['id'])[0]
        self.assertIn('country_programme', intervention_data)
        self.assertEqual(country_programme.id, intervention_data['country_programme'])

    def test_intervention_list_filter_by_budget_owner(self):
        first_budget_owner = UserFactory()
        second_budget_owner = UserFactory()
        interventions = [
            GDDFactory(budget_owner=first_budget_owner).id,
            GDDFactory(budget_owner=second_budget_owner).id,
        ]
        GDDFactory()
        GDDFactory()
        response = self.forced_auth_req(
            'get',
            reverse('governments:gdd-list'),
            user=self.unicef_user,
            QUERY_STRING=f'budget_owner__in={first_budget_owner.id},{second_budget_owner.id}'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertCountEqual(
            [i['id'] for i in response.data],
            interventions,
        )


class TestDetail(BaseGDDTestCase):
    def setUp(self):
        super().setUp()
        self.gdd = GDDFactory(
            partner=self.partner,
            unicef_signatory=self.unicef_user,
            date_sent_to_partner=datetime.date.today()
        )
        frs = FundsReservationHeaderFactory(
            gdd=self.gdd,
            currency='USD',
        )
        FundsReservationItemFactory(fund_reservation=frs)
        result = EWPOutputFactory(
            cp_output__result_type__name=ResultType.OUTPUT,
        )
        link = GDDResultLinkFactory(
            cp_output=result,
            gdd=self.gdd,
            workplan=result.workplan
        )
        key_intervention = GDDKeyInterventionFactory(result_link=link)
        GDDActivityFactory(key_intervention=key_intervention, unicef_cash=10, ewp_activity=EWPActivityFactory())

    def test_get(self):
        response = self.forced_auth_req(
            "get",
            reverse('governments:gdd-detail', args=[self.gdd.pk]),
            user=self.unicef_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data["id"], self.gdd.pk)
        self.assertEqual(data["result_links"][0]["total"], 10)
        self.assertIn('created', data["result_links"][0])
        self.assertEqual(data["unicef_signatory"], self.user_serialized)
        self.assertIn('confidential', data)

    @skip
    def test_pdf(self):
        response = self.forced_auth_req(
            "get",
            reverse(
                'governments:gdd-detail-pdf',
                args=[self.gdd.pk],
            ),
            user=self.unicef_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    @skip
    def test_pdf_unauthenticated_user_forbidden(self):
        """Ensure an unauthenticated user gets the 403 forbidden"""
        response = APIClient().get(
            reverse(
                'governments:gdd-detail-pdf',
                args=[self.gdd.pk],
            )
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_reporting_requirements_partner_user(self):
        staff_member = UserFactory(
            realms__data=['IP Viewer'],
            profile__organization=self.gdd.partner.organization,
        )
        self.gdd.partner_focal_points.add(staff_member)
        response = self.forced_auth_req(
            "get",
            reverse('governments:gdd-detail', args=[self.gdd.pk]),
            user=staff_member,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['permissions']['view']['reporting_requirements'])

    def test_confidential_permissions_unicef(self):
        self.gdd.unicef_focal_points.add(self.unicef_user)
        response = self.forced_auth_req(
            "get",
            reverse('governments:gdd-detail', args=[self.gdd.pk]),
            user=self.unicef_user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['permissions']['view']['confidential'])
        self.assertTrue(response.data['permissions']['edit']['confidential'])

    def test_confidential_permissions_partner_user(self):
        staff_member = UserFactory(
            realms__data=['IP Viewer'],
            profile__organization=self.gdd.partner.organization,
        )
        self.gdd.partner_focal_points.add(staff_member)
        response = self.forced_auth_req(
            "get",
            reverse('governments:gdd-detail', args=[self.gdd.pk]),
            user=staff_member
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['permissions']['view']['confidential'])
        self.assertFalse(response.data['permissions']['edit']['confidential'])

    @skip
    def test_pdf_partner_user(self):
        staff_member = UserFactory(
            realms__data=['IP Viewer'],
            profile__organization=self.gdd.partner.organization,
        )
        self.gdd.partner_focal_points.add(staff_member)
        response = self.forced_auth_req(
            "get",
            reverse('governments:gdd-detail-pdf', args=[self.gdd.pk]),
            user=staff_member,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    @skip
    def test_pdf_another_partner_user(self):
        staff_member = UserFactory(
            realms__data=['IP Viewer'],
            profile__organization=OrganizationFactory(),
        )
        response = self.forced_auth_req(
            "get",
            reverse('governments:gdd-detail-pdf', args=[self.gdd.pk]),
            user=staff_member,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @skip
    def test_pdf_not_found(self):
        response = self.forced_auth_req(
            "get",
            reverse(
                'governments:gdd-detail-pdf',
                args=[40404],
            ),
            user=self.unicef_user,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # test available actions
    def test_available_actions_unicef_review(self):
        self.gdd.date_sent_to_partner = datetime.date.today()
        self.gdd.unicef_accepted = True
        self.gdd.partner_accepted = True
        self.gdd.budget_owner = self.unicef_user
        self.gdd.save()
        GDDReviewFactory(gdd=self.gdd, review_type='prc')

        response = self.forced_auth_req(
            "get",
            reverse('governments:gdd-detail', args=[self.gdd.pk]),
            user=self.unicef_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("review", response.data["available_actions"])

    def test_available_actions_unicef_review_not_accepted(self):
        self.gdd.date_sent_to_partner = datetime.date.today()
        self.gdd.unicef_accepted = True
        self.gdd.partner_accepted = False
        self.gdd.budget_owner = self.unicef_user
        self.gdd.save()

        response = self.forced_auth_req(
            "get",
            reverse('governments:gdd-detail', args=[self.gdd.pk]),
            user=self.unicef_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("review", response.data["available_actions"])

    def test_available_actions_overall_reviewer_sign(self):
        self.gdd.date_sent_to_partner = datetime.date.today()
        self.gdd.unicef_accepted = True
        self.gdd.partner_accepted = True
        self.gdd.budget_owner = self.unicef_user
        self.gdd.status = GDD.REVIEW
        self.gdd.save()
        GDDReviewFactory(gdd=self.gdd, review_type='prc', overall_approver=UserFactory())
        GDDReviewFactory(gdd=self.gdd, review_type='prc', overall_approver=self.unicef_user)

        response = self.forced_auth_req(
            "get",
            reverse('governments:gdd-detail', args=[self.gdd.pk]),
            user=self.unicef_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # self.assertIn("sign", response.data["available_actions"])
        self.assertIn("reject_review", response.data["available_actions"])

    def test_available_actions_review_prc_secretary(self):
        self.gdd.date_sent_to_partner = datetime.date.today()
        self.gdd.unicef_accepted = True
        self.gdd.partner_accepted = True
        self.gdd.status = GDD.REVIEW
        self.gdd.save()
        GDDReviewFactory(gdd=self.gdd, review_type='prc', overall_approval=None)
        RealmFactory(
            user=self.unicef_user,
            country=CountryFactory(),
            organization=self.partner.organization,
            group=GroupFactory(name=PRC_SECRETARY))

        response = self.forced_auth_req(
            "get",
            reverse('governments:gdd-detail', args=[self.gdd.pk]),
            user=self.unicef_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("send_back_review", response.data["available_actions"])

    def test_empty_actions_while_cancelled(self):
        self.gdd.status = GDD.CANCELLED
        self.gdd.budget_owner = self.unicef_user
        self.gdd.save()
        response = self.forced_auth_req(
            "get",
            reverse('governments:gdd-detail', args=[self.gdd.pk]),
            user=self.unicef_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertListEqual(
            ['download_comments', 'export_pdf', 'export_xls'],
            response.data["available_actions"],
        )

    def test_num_queries(self):
        # clear waffle cache to avoid queries number inconsistency caused by cached tenant flags
        get_cache().clear()

        # TODO improve queries
        with self.assertNumQueries(51):
            response = self.forced_auth_req(
                "get",
                reverse('governments:gdd-detail', args=[self.gdd.pk]),
                user=self.unicef_user
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_planned_budget_total_supply(self):
        count = 5
        for __ in range(count):
            GDDSupplyItemFactory(
                gdd=self.gdd,
                unit_number=1,
                unit_price=1,
                provided_by=GDDSupplyItem.PROVIDED_BY_PARTNER
            )
        for __ in range(count):
            GDDSupplyItemFactory(
                gdd=self.gdd,
                unit_number=1,
                unit_price=2,
                provided_by=GDDSupplyItem.PROVIDED_BY_UNICEF
            )
        response = self.forced_auth_req(
            "get",
            reverse('governments:gdd-detail', args=[self.gdd.pk]),
            user=self.unicef_user
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('planned_budget', response.data)
        self.assertEqual(response.data['planned_budget']['total_supply'],
                         str(self.gdd.planned_budget.total_supply))
        self.assertEqual(response.data['planned_budget']['total_supply'],
                         str(self.gdd.planned_budget.in_kind_amount_local +
                             self.gdd.planned_budget.partner_supply_local))


class TestCreate(BaseGDDTestCase):
    def test_post(self):
        data = {
            "title": "PMP GDD",
            "partner": self.partner.pk,
            "reference_number_year": timezone.now().year,
            "budget_owner": self.unicef_user.pk,
            "start": timezone.now().date(),
            "end": timezone.now().date() + datetime.timedelta(days=300)
        }
        response = self.forced_auth_req(
            "post",
            reverse('governments:gdd-list'),
            user=self.unicef_user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        data = response.data
        i = GDD.objects.get(pk=response.data.get("id"))
        self.assertEqual(i.start.strftime('%Y-%m-%d'), response.data['start'])
        self.assertEqual(i.end.strftime('%Y-%m-%d'), response.data['end'])
        self.assertEqual(i.partner.pk.__str__(), response.data['partner_id'])
        self.assertEqual(data.get("budget_owner"), self.user_serialized)

    def test_add_intervention_by_partner_member(self):
        partner_user = UserFactory(
            realms__data=['IP Viewer'],
            profile__organization=self.partner.organization,
        )
        response = self.forced_auth_req(
            "post",
            reverse('governments:gdd-list'),
            user=partner_user,
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_add_intervention_by_anonymous(self):
        response = self.forced_auth_req(
            "post",
            reverse('governments:gdd-list'),
            user=AnonymousUser(),
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_add_minimal_intervention(self):
        response = self.forced_auth_req(
            "post",
            reverse('governments:gdd-list'),
            user=self.unicef_user,
            data={
                'title': 'My test gdd',
                'partner': self.partner.pk,
                "country_programme": CountryProgrammeFactory().pk,
                'reference_number_year': timezone.now().year
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_add_currency(self):
        response = self.forced_auth_req(
            "post",
            reverse('governments:gdd-list'),
            user=self.unicef_user,
            data={
                'title': 'PD with Currency',
                'partner': self.partner.pk,
                "country_programme": CountryProgrammeFactory().pk,
                'reference_number_year': timezone.now().year,
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
        pd = GDD.objects.get(pk=response.data["id"])
        self.assertEqual(pd.planned_budget.currency, 'AFN')

    def test_add_currency_invalid(self):
        response = self.forced_auth_req(
            "post",
            reverse('governments:gdd-list'),
            user=self.unicef_user,
            data={
                'title': 'PD with Currency',
                'partner': self.partner.pk,
                "country_programme": CountryProgrammeFactory().pk,
                'reference_number_year': timezone.now().year,
                'planned_budget': {
                    'currency': 'WRONG',
                }
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_invalid_character_limit(self):
        data = {
            "title": "PMP GDD",
            "context": "long text" * 5000,
            "implementation_strategy": "long text" * 5000,
            "ip_program_contribution": "long text" * 5000,
            "other_details": "*" * 5001,
        }
        response = self.forced_auth_req(
            "post",
            reverse('governments:gdd-list'),
            user=self.unicef_user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        for field_name, max_length in [
            ("context", 7000),
            ("implementation_strategy", 5000),
            ("ip_program_contribution", 5000),
            ("other_details", 5000),
        ]:
            self.assertEqual(
                response.data[field_name],
                ["This field is limited to {0} or less characters.".format(max_length)],
            )

    def test_post_sections(self):
        lead_section = SectionFactory()
        sections = [SectionFactory().pk, SectionFactory().pk]

        data = {
            "title": "PMP GDD",
            "partner": self.partner.pk,
            "reference_number_year": timezone.now().year,
            "budget_owner": self.unicef_user.pk,
            "start": timezone.now().date(),
            "end": timezone.now().date() + datetime.timedelta(days=300),
            "lead_section": lead_section.pk,
            "sections": sections
        }
        response = self.forced_auth_req(
            "post",
            reverse('governments:gdd-list'),
            user=self.unicef_user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        data = response.data
        self.assertEqual(data['lead_section'], lead_section.pk)
        self.assertEqual(data['lead_section_name'], lead_section.name)
        i = GDD.objects.get(pk=response.data.get("id"))
        self.assertEqual(i.lead_section, lead_section)
        self.assertEqual(list(i.sections.all().values_list('id', flat=True)), sections)

    def test_post_sections_bad_request(self):
        lead_section = SectionFactory()
        sections = [lead_section.pk, SectionFactory().pk, SectionFactory().pk]

        data = {
            "title": "PMP GDD",
            "partner": self.partner.pk,
            "reference_number_year": timezone.now().year,
            "budget_owner": self.unicef_user.pk,
            "start": timezone.now().date(),
            "end": timezone.now().date() + datetime.timedelta(days=300),
            "lead_section": lead_section.pk,
            "sections": sections
        }
        response = self.forced_auth_req(
            "post",
            reverse('governments:gdd-list'),
            user=self.unicef_user,
            data=data
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn('The Lead Section is also selected in Contributing Sections.', response.data)


class TestUpdate(BaseGDDTestCase):
    def setUp(self):
        super().setUp()
        # call_command("update_notifications")

    def test_patch_currency(self):
        gdd = GDDFactory()
        gdd.unicef_focal_points.add(self.unicef_user)
        budget = gdd.planned_budget
        self.assertNotEqual(budget.currency, "PEN")

        response = self.forced_auth_req(
            "patch",
            reverse('governments:gdd-detail', args=[gdd.pk]),
            user=self.unicef_user,
            data={'planned_budget': {
                "id": budget.pk,
                "currency": "PEN",
            }}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        budget.refresh_from_db()
        self.assertEqual(budget.currency, "PEN")

    def test_patch_lead_section_sections(self):
        gdd = GDDFactory()
        gdd.unicef_focal_points.add(self.unicef_user)
        lead_section = SectionFactory()
        sections = [SectionFactory().pk, SectionFactory().pk]

        response = self.forced_auth_req(
            "patch",
            reverse('governments:gdd-detail', args=[gdd.pk]),
            user=self.unicef_user,
            data={'lead_section': lead_section.pk, 'sections': sections}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        gdd.refresh_from_db()
        self.assertEqual(gdd.lead_section, lead_section)
        self.assertEqual(list(gdd.sections.all().values_list('id', flat=True)), sections)

    def test_patch_sections_bad_request(self):
        gdd = GDDFactory()
        gdd.unicef_focal_points.add(self.unicef_user)
        lead_section = SectionFactory()
        sections = [lead_section, SectionFactory(), SectionFactory()]

        response = self.forced_auth_req(
            "patch",
            reverse('governments:gdd-detail', args=[gdd.pk]),
            user=self.unicef_user,
            data={'lead_section': lead_section.pk, 'sections': [s.pk for s in sections]}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('The Lead Section is also selected in Contributing Sections.', response.data)
        gdd.refresh_from_db()
        self.assertEqual(gdd.lead_section, None)
        self.assertEqual(gdd.sections.count(), 0)

        gdd.lead_section = lead_section
        gdd.save(update_fields=['lead_section'])
        response = self.forced_auth_req(
            "patch",
            reverse('governments:gdd-detail', args=[gdd.pk]),
            user=self.unicef_user,
            data={'sections': [s.pk for s in sections]}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('The Lead Section is also selected in Contributing Sections.', response.data)
        gdd.refresh_from_db()
        self.assertEqual(gdd.lead_section, lead_section)
        self.assertEqual(gdd.sections.count(), 0)

        section = SectionFactory()
        gdd.sections.add(section)
        gdd.sections.add(SectionFactory())
        response = self.forced_auth_req(
            "patch",
            reverse('governments:gdd-detail', args=[gdd.pk]),
            user=self.unicef_user,
            data={'lead_section': section.pk}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('The Lead Section is also selected in Contributing Sections.', response.data)
        gdd.refresh_from_db()
        self.assertEqual(gdd.lead_section, lead_section)
        self.assertEqual(gdd.sections.count(), 2)

    def test_flat_locations_update_signal(self):
        gdd = GDDFactory()
        gdd.unicef_focal_points.add(self.unicef_user)
        self.assertEqual(gdd.flat_locations.count(), 0)

        activity = GDDActivityFactory(key_intervention__result_link__gdd=gdd)
        self.assertEqual(gdd.flat_locations.count(), 1)
        self.assertEqual(list(gdd.flat_locations.all()), list(activity.locations.all()))

        a_loc = LocationFactory()
        activity.locations.add(a_loc)
        self.assertEqual(gdd.flat_locations.count(), 2)
        self.assertEqual(list(gdd.flat_locations.all()), list(activity.locations.all()))

        activity.locations.remove(a_loc)
        new_loc = LocationFactory()
        activity.locations.add(new_loc)
        self.assertEqual(activity.locations.count(), 2)
        self.assertEqual(gdd.flat_locations.count(), 2)
        self.assertEqual(list(gdd.flat_locations.all()), list(activity.locations.all()))

        activity.locations.clear()
        self.assertEqual(activity.locations.count(), 0)
        self.assertEqual(gdd.flat_locations.count(), 0)

    @skip
    def test_patch_frs_prc_secretary(self):
        gdd = GDDFactory()
        prc_secretary = UserFactory(
            is_staff=True, realms__data=[UNICEF_USER, PRC_SECRETARY]
        )

        fr = FundsReservationHeaderFactory(gdd=None, currency='USD')
        self.assertEqual(FundsReservationHeader.objects.filter(gdd=gdd).count(), 0)
        response = self.forced_auth_req(
            "patch",
            reverse('governments:gdd-detail', args=[gdd.pk]),
            user=prc_secretary,
            data={'frs': [fr.id]}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(FundsReservationHeader.objects.filter(gdd=gdd).count(), 1)

    def test_patch_country_programme_by_unicef_focal_point(self):
        gdd = GDDFactory()
        gdd.unicef_focal_points.add(self.unicef_user)
        cp = CountryProgrammeFactory()
        self.assertNotEqual(gdd.country_programme, cp)

        response = self.forced_auth_req(
            "patch",
            reverse('governments:gdd-detail', args=[gdd.pk]),
            user=self.unicef_user,
            data={
                "country_programme": cp.pk,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        gdd.refresh_from_db()
        self.assertEqual(cp, gdd.country_programme)

    def test_patch_e_workplans_by_unicef_focal_point(self):
        gdd = GDDFactory()
        gdd.unicef_focal_points.add(self.unicef_user)
        e_workplan_1 = GovernmentEWPFactory()
        e_workplan_2 = GovernmentEWPFactory()
        self.assertNotIn(e_workplan_1, gdd.e_workplans.all())
        self.assertNotIn(e_workplan_2, gdd.e_workplans.all())

        response = self.forced_auth_req(
            "patch",
            reverse('governments:gdd-detail', args=[gdd.pk]),
            user=self.unicef_user,
            data={
                "e_workplans": [e_workplan_1.pk, e_workplan_2.pk],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        gdd.refresh_from_db()
        self.assertTrue(e_workplan_1 in gdd.e_workplans.all())
        self.assertTrue(e_workplan_2 in gdd.e_workplans.all())

    # def test_update_hq_cash_local(self):
    #     gdd = GDDFactory()
    #     gdd.unicef_focal_points.add(self.unicef_user)
    #     budget = gdd.planned_budget
    #
    #     GDDActivityFactory(
    #         result__result_link=GDDResultLinkFactory(
    #             cp_output__result_type__name=ResultType.OUTPUT,
    #             gdd=gdd
    #         ),
    #         unicef_cash=40,
    #     )
    #
    #     budget.refresh_from_db()
    #     self.assertEqual(budget.total_hq_cash_local, 0)
    #     self.assertEqual(budget.unicef_cash_local, 40)
    #
    #     response = self.forced_auth_req(
    #         "patch",
    #         reverse('governments:gdd-detail', args=[gdd.pk]),
    #         user=self.unicef_user,
    #         data={'planned_budget': {
    #             "id": budget.pk,
    #             "total_hq_cash_local": "10.00",
    #         }}
    #     )
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     budget.refresh_from_db()
    #     self.assertEqual(budget.total_hq_cash_local, 10)
    #     self.assertEqual(budget.unicef_cash_local, 50)
    #
    # def test_fields_required_on_unicef_accept(self):
    #     gdd = GDDFactory(
    #         ip_program_contribution='contribution',
    #         status=GDD.DRAFT,
    #         unicef_accepted=False,
    #         partner_accepted=False,
    #         agreement__partner=self.partner,
    #         date_sent_to_partner=timezone.now(),
    #         partner_authorized_officer_signatory=None,
    #         signed_by_partner_date=None,
    #         signed_by_unicef_date=None,
    #     )
    #     ReportingRequirementFactory(gdd=gdd, start_date=gdd.start, end_date=gdd.end)
    #     gdd.flat_locations.add(LocationFactory())
    #     gdd.unicef_focal_points.add(self.unicef_user)
    #     staff_member = UserFactory(
    #         realms__data=['IP Viewer'],
    #         profile__organization=self.partner.organization
    #     )
    #     gdd.partner_focal_points.add(staff_member)
    #     response = self.forced_auth_req(
    #         "patch",
    #         reverse('governments:gdd-detail', args=[gdd.pk]),
    #         user=self.unicef_user,
    #         data={}
    #     )
    #     self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
    #
    #     gdd.unicef_court = False
    #     gdd.save()
    #     gdd.sections.add(SectionFactory())
    #     result_link = GDDResultLinkFactory(
    #         gdd=gdd,
    #         cp_output__result_type__name=ResultType.OUTPUT,
    #         ram_indicators=[IndicatorFactory()],
    #     )
    #     pd_output = LowerResultFactory(result_link=result_link)
    #     AppliedIndicatorFactory(lower_result=pd_output, section=gdd.sections.first())
    #     activity = GDDActivityFactory(result=pd_output)
    #     activity.time_frames.add(gdd.quarters.first())
    #     response = self.forced_auth_req(
    #         "patch",
    #         reverse('governments:gdd-accept', args=[gdd.pk]),
    #         user=staff_member,
    #     )
    #     self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
    #     response = self.forced_auth_req(
    #         "patch",
    #         reverse('governments:gdd-accept', args=[gdd.pk]),
    #         user=self.unicef_user,
    #     )
    #     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
    #     self.assertIn('Required fields not completed in draft', response.data[0]['description'])
    #
    #     # check pending_approval fields are not required in this case
    #     for field in [
    #         'signed_pd_attachment', 'date_sent_to_partner', 'signed_by_unicef_date',
    #         'signed_by_partner_date', 'partner_authorized_officer_signatory',
    #     ]:
    #         self.assertNotIn(field, response.data[0])
    #
    def test_update_context_characters_limitation_ok(self):
        gdd = GDDFactory()
        gdd.unicef_focal_points.add(self.unicef_user)
        response = self.forced_auth_req(
            "patch",
            reverse('governments:gdd-detail', args=[gdd.pk]),
            user=self.unicef_user,
            data={'context': '*' * 7000},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_update_context_characters_limitation_fail(self):
        gdd = GDDFactory(status=GDD.DRAFT)
        gdd.unicef_focal_points.add(self.unicef_user)
        response = self.forced_auth_req(
            "patch",
            reverse('governments:gdd-detail', args=[gdd.pk]),
            user=self.unicef_user,
            data={'context': '*' * 7001},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn('context', response.data)


# class TestDelete(BaseGDDTestCase):
#     def setUp(self):
#         super().setUp()
#         self.gdd = GDDFactory()
#         self.unicef_user = UserFactory(is_staff=True)
#         self.partner_user = UserFactory(
#             realms__data=['IP Viewer'],
#             profile__organization=self.gdd.partner.organization
#         )
#         self.gdd.partner_focal_points.add(self.partner_user)
#         self.intervention_qs = GDD.objects.filter(
#             pk=self.gdd.pk,
#         )
#
#     def test_with_date_sent_to_partner_reset(self):
#         # attempt clear date sent, but with snapshot
#         pre_save = create_dict_with_relations(self.gdd)
#         self.gdd.date_sent_to_partner = None
#         self.gdd.save()
#         create_snapshot(self.gdd, pre_save, self.unicef_user)
#
#         self.assertTrue(self.intervention_qs.exists())
#         response = self.forced_auth_req(
#             "delete",
#             reverse('governments:gdd-delete', args=[self.gdd.pk]),
#             user=self.unicef_user,
#         )
#         self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
#         self.assertFalse(self.intervention_qs.exists())
#
#     def test_delete_partner(self):
#         self.assertTrue(self.intervention_qs.exists())
#         response = self.forced_auth_req(
#             "delete",
#             reverse('governments:gdd-delete', args=[self.gdd.pk]),
#             user=self.partner_user,
#         )
#         self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
#         self.assertTrue(self.intervention_qs.exists())
