from django.urls import reverse

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import Intervention, InterventionResultLink
from etools.applications.partners.tests.factories import (
    InterventionFactory,
    InterventionResultLinkFactory,
    PartnerStaffFactory,
)
from etools.applications.reports.models import LowerResult, ResultType
from etools.applications.reports.tests.factories import LowerResultFactory, ResultFactory
from etools.applications.users.tests.factories import UserFactory


class TestInterventionLowerResultsViewBase(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        self.user = UserFactory(is_staff=True, groups__data=['Partnership Manager', 'UNICEF User'])
        self.intervention = InterventionFactory(status=Intervention.DRAFT, unicef_court=True)

        self.staff_member = PartnerStaffFactory(partner=self.intervention.agreement.partner)
        self.partner_focal_point = UserFactory(groups__data=[], profile__partner_staff_member=self.staff_member.id)
        self.intervention.partner_focal_points.add(self.staff_member)

        self.cp_output = ResultFactory(result_type__name=ResultType.OUTPUT)
        self.result_link = InterventionResultLinkFactory(intervention=self.intervention, cp_output=self.cp_output)


class TestInterventionLowerResultsListView(TestInterventionLowerResultsViewBase):
    def setUp(self):
        super().setUp()
        self.list_url = reverse('partners:intervention-pd-output-list', args=[self.intervention.pk])

    # check global functionality
    def test_list(self):
        LowerResultFactory(result_link=InterventionResultLinkFactory(intervention=self.intervention, cp_output=None))
        LowerResultFactory(result_link=self.result_link)

        response = self.forced_auth_req('get', self.list_url, self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(len(response.data), 2)
        self.assertEqual([r['cp_output'] for r in response.data], [None, self.cp_output.id])

    def test_create_unassociated(self):
        response = self.forced_auth_req('post', self.list_url, self.user, data={'name': 'test'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        pd_result = LowerResult.objects.get(id=response.data['id'])
        self.assertEqual(pd_result.result_link.intervention, self.intervention)
        self.assertEqual(pd_result.result_link.cp_output, None)

    def test_create_associated(self):
        response = self.forced_auth_req(
            'post', self.list_url, self.user,
            data={'name': 'test', 'cp_output': self.cp_output.id}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        pd_result = LowerResult.objects.get(id=response.data['id'])
        self.assertEqual(pd_result.result_link.intervention, self.intervention)
        self.assertEqual(pd_result.result_link.cp_output, self.cp_output)

    def test_intervention_provided_on_create(self):
        response = self.forced_auth_req(
            'post', self.list_url, self.user,
            data={'name': 'test', 'code': 'test', 'cp_output': self.cp_output.id}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertIn('intervention', response.data)

    def test_intervention_missing_on_list(self):
        response = self.forced_auth_req('get', self.list_url, self.user,)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertNotIn('intervention', response.data)

    # check permissions
    def test_create_for_unknown_user(self):
        response = self.forced_auth_req(
            'post', self.list_url, UserFactory(groups__data=[]),
            data={'name': 'test', 'cp_output': self.cp_output.id}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_create_for_signed_intervention(self):
        self.intervention.status = Intervention.SIGNED
        self.intervention.save()

        response = self.forced_auth_req(
            'post', self.list_url, self.user,
            data={'name': 'test', 'cp_output': self.cp_output.id}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_create_assigned_partner_user_unicef_court(self):
        response = self.forced_auth_req(
            'post', self.list_url, self.partner_focal_point,
            data={'name': 'test', 'cp_output': self.cp_output.id}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_create_assigned_partner_user_partner_court(self):
        self.intervention.unicef_court = False
        self.intervention.save()

        response = self.forced_auth_req(
            'post', self.list_url, self.partner_focal_point,
            data={'name': 'test', 'cp_output': self.cp_output.id}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        pd_result = LowerResult.objects.get(id=response.data['id'])
        self.assertEqual(pd_result.result_link.cp_output, None)

    def test_create_assigned_partner_user_signed_intervention(self):
        self.intervention.unicef_court = False
        self.intervention.status = Intervention.SIGNED
        self.intervention.save()

        response = self.forced_auth_req(
            'post', self.list_url, self.partner_focal_point,
            data={'name': 'test', 'cp_output': self.cp_output.id}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_create_unassigned_partner_user(self):
        self.intervention.unicef_court = False
        self.intervention.partner_focal_points.clear()
        self.intervention.save()

        response = self.forced_auth_req(
            'post', self.list_url, self.partner_focal_point,
            data={'name': 'test', 'cp_output': self.cp_output.id}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)


class TestInterventionLowerResultsDetailView(TestInterventionLowerResultsViewBase):
    # check global functionality
    def test_associate_output(self):
        old_result_link = InterventionResultLinkFactory(intervention=self.intervention, cp_output=None)
        result = LowerResultFactory(result_link=old_result_link)
        response = self.forced_auth_req(
            'patch',
            reverse('partners:intervention-pd-output-detail', args=[self.intervention.pk, result.pk]),
            self.user,
            data={'cp_output': self.result_link.cp_output.id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['cp_output'], self.result_link.cp_output.id)
        self.assertFalse(InterventionResultLink.objects.filter(pk=old_result_link.pk).exists())

        result.refresh_from_db()
        self.assertEqual(result.result_link, self.result_link)

    def test_associate_output_if_other_exists(self):
        old_result_link = InterventionResultLinkFactory(intervention=self.intervention, cp_output=None)
        result = LowerResultFactory(result_link=old_result_link)
        LowerResultFactory(result_link=old_result_link)
        self.assertEqual(old_result_link.ll_results.count(), 2)
        response = self.forced_auth_req(
            'patch',
            reverse('partners:intervention-pd-output-detail', args=[self.intervention.pk, result.pk]),
            self.user,
            data={'cp_output': self.result_link.cp_output.id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['cp_output'], self.result_link.cp_output.id)
        self.assertTrue(InterventionResultLink.objects.filter(pk=old_result_link.pk).exists())
        self.assertEqual(old_result_link.ll_results.count(), 1)

    def test_associate_two_outputs_duplicated_code(self):
        first_pd_output = LowerResultFactory(
            result_link=InterventionResultLinkFactory(
                intervention=self.intervention, cp_output__result_type__name=ResultType.OUTPUT
            ),
            code=None
        )
        second_pd_output = LowerResultFactory(
            result_link=InterventionResultLinkFactory(
                intervention=self.intervention, cp_output__result_type__name=ResultType.OUTPUT
            ),
            code=None
        )

        # two pd outputs have same codes, so unique together by result_link + code will raise error without more logic
        self.assertEqual(first_pd_output.code, second_pd_output.code)
        first_response = self.forced_auth_req(
            'patch',
            reverse('partners:intervention-pd-output-detail', args=[self.intervention.pk, first_pd_output.pk]),
            self.user,
            data={'cp_output': self.result_link.cp_output.id}
        )
        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        second_response = self.forced_auth_req(
            'patch',
            reverse('partners:intervention-pd-output-detail', args=[self.intervention.pk, second_pd_output.pk]),
            self.user,
            data={'cp_output': self.result_link.cp_output.id}
        )
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)

    def test_deassociate_temp_output(self):
        old_result_link = InterventionResultLinkFactory(intervention=self.intervention, cp_output=None)
        result = LowerResultFactory(result_link=old_result_link)
        response = self.forced_auth_req(
            'patch',
            reverse('partners:intervention-pd-output-detail', args=[self.intervention.pk, result.pk]),
            self.user,
            data={'cp_output': None}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['cp_output'], None)

        result.refresh_from_db()
        self.assertEqual(result.result_link, old_result_link)

    def test_deassociate_good_output(self):
        result = LowerResultFactory(result_link=self.result_link)
        response = self.forced_auth_req(
            'patch',
            reverse('partners:intervention-pd-output-detail', args=[self.intervention.pk, result.pk]),
            self.user,
            data={'cp_output': None}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['cp_output'], None)

        result.refresh_from_db()
        self.assertNotEqual(result.result_link, self.result_link)
        self.assertEqual(result.result_link.cp_output, None)

    # permissions are common with list view and were explicitly checked in corresponding api test case

    def test_associate_output_as_partner(self):
        self.intervention.unicef_court = False
        self.intervention.save()

        result = LowerResultFactory(
            result_link=InterventionResultLinkFactory(intervention=self.intervention, cp_output=None)
        )
        response = self.forced_auth_req(
            'patch',
            reverse('partners:intervention-pd-output-detail', args=[self.intervention.pk, result.pk]),
            self.partner_focal_point,
            data={'cp_output': self.result_link.cp_output.id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        result.refresh_from_db()
        self.assertEqual(result.result_link.cp_output, None)

    def test_intervention_provided_on_update(self):
        result = LowerResultFactory(result_link=self.result_link)
        response = self.forced_auth_req(
            'patch',
            reverse('partners:intervention-pd-output-detail', args=[self.intervention.pk, result.pk]),
            self.user, data={}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertIn('intervention', response.data)

    def test_intervention_missing_on_retrieve(self):
        result = LowerResultFactory(result_link=self.result_link)
        response = self.forced_auth_req(
            'get',
            reverse('partners:intervention-pd-output-detail', args=[self.intervention.pk, result.pk]),
            self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertNotIn('intervention', response.data)
