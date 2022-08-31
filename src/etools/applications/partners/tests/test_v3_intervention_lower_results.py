import itertools

from django.urls import reverse

from rest_framework import status
from unicef_locations.tests.factories import LocationFactory
from unicef_snapshot.models import Activity

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import Intervention, InterventionResultLink
from etools.applications.partners.permissions import PARTNERSHIP_MANAGER_GROUP, UNICEF_USER
from etools.applications.partners.tests.factories import (
    InterventionFactory,
    InterventionResultLinkFactory,
    PartnerStaffFactory,
)
from etools.applications.reports.models import LowerResult, ResultType
from etools.applications.reports.tests.factories import (
    AppliedIndicatorFactory,
    InterventionActivityFactory,
    InterventionActivityItemFactory,
    LowerResultFactory,
    ResultFactory,
    SectionFactory,
)
from etools.applications.users.tests.factories import UserFactory


class TestInterventionLowerResultsViewBase(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        self.user = UserFactory(is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP])
        self.intervention = InterventionFactory(status=Intervention.DRAFT, unicef_court=True)

        self.partner_focal_point = UserFactory(realms__data=[])
        self.staff_member = PartnerStaffFactory(
            partner=self.intervention.agreement.partner,
            user=self.partner_focal_point,
        )
        self.intervention.partner_focal_points.add(self.staff_member)
        self.intervention.unicef_focal_points.add(self.user)

        self.partner_staff_member = PartnerStaffFactory(partner=self.intervention.agreement.partner).user

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
        self.assertEqual(pd_result.code, '0.1')

    def test_create_associated(self):
        response = self.forced_auth_req(
            'post', self.list_url, self.user,
            data={'name': 'test', 'cp_output': self.cp_output.id}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        pd_result = LowerResult.objects.get(id=response.data['id'])
        self.assertEqual(pd_result.result_link.intervention, self.intervention)
        self.assertEqual(pd_result.result_link.cp_output, self.cp_output)
        self.assertEqual(pd_result.code, '1.1')

    def test_create_associated_invalid_cp_output(self):
        cp_output = ResultFactory(result_type__name=ResultType.OUTPUT)
        cp_output_qs = InterventionResultLink.objects.filter(
            intervention=self.intervention,
            cp_output=cp_output,
        )
        self.assertFalse(cp_output_qs.exists())
        response = self.forced_auth_req(
            'post',
            self.list_url,
            self.user,
            data={'name': 'test', 'cp_output': cp_output.pk},
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            response.data,
        )
        self.assertIn("cp_output", response.data)
        self.assertFalse(cp_output_qs.exists())

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
            'post', self.list_url, UserFactory(realms__data=[]),
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
        InterventionActivityFactory(result=result, unicef_cash=10, cso_cash=20)
        response = self.forced_auth_req(
            'patch',
            reverse('partners:intervention-pd-output-detail', args=[self.intervention.pk, result.pk]),
            self.user,
            data={'cp_output': self.result_link.cp_output.id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['cp_output'], self.result_link.cp_output.id)
        self.assertFalse(InterventionResultLink.objects.filter(pk=old_result_link.pk).exists())
        self.assertEqual(response.data['total'], result.total())
        for links in response.data["intervention"]["result_links"]:
            self.assertIn("total", links)
            for ll_result in links["ll_results"]:
                self.assertIn("total", ll_result)

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

    def test_associate_two_outputs(self):
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
        self.assertEqual(first_response.data['cp_output'], second_response.data['cp_output'])

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

    def test_delete_unassociated_pd_output(self):
        result_link = InterventionResultLinkFactory(intervention=self.intervention, cp_output=None)
        result = LowerResultFactory(result_link=result_link)
        InterventionActivityFactory(result=result, unicef_cash=10, cso_cash=20)
        response = self.forced_auth_req(
            'delete',
            reverse('partners:intervention-pd-output-detail', args=[self.intervention.pk, result.pk]),
            self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertFalse(InterventionResultLink.objects.filter(pk=result_link.pk).exists())

    def assign_result_to_cp_output(self, lower_result, cp_output):
        response = self.forced_auth_req(
            'patch',
            reverse('partners:intervention-pd-output-detail', args=[self.intervention.pk, lower_result.pk]),
            self.user,
            data={'cp_output': cp_output.id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return response

    def test_associate_output_renumber_codes_activities(self):
        self.assertEqual(self.result_link.code, '1')
        self.assertEqual(LowerResultFactory(code=None, result_link=self.result_link).code, '1.1')
        old_result_link = InterventionResultLinkFactory(code=None, intervention=self.intervention, cp_output=None)
        result = LowerResultFactory(code=None, result_link=old_result_link)
        activity = InterventionActivityFactory(code=None, result=result)
        self.assertEqual(result.code, '0.1')
        self.assertEqual(activity.code, '0.1.1')
        self.assign_result_to_cp_output(result, self.result_link.cp_output)
        result.refresh_from_db()
        activity.refresh_from_db()
        self.assertEqual(result.code, '1.2')
        self.assertEqual(activity.code, '1.2.1')

    def test_associate_output_renumber_codes_activity_items(self):
        self.assertEqual(self.result_link.code, '1')
        self.assertEqual(LowerResultFactory(code=None, result_link=self.result_link).code, '1.1')
        old_result_link = InterventionResultLinkFactory(code=None, intervention=self.intervention, cp_output=None)
        result = LowerResultFactory(code=None, result_link=old_result_link)
        activity = InterventionActivityFactory(code=None, result=result)
        quarter = self.intervention.quarters.first()
        act_item = InterventionActivityItemFactory(activity=activity, unicef_cash=8)
        quarter.activities.add(activity)

        self.assertEqual(result.code, '0.1')
        self.assertEqual(activity.code, '0.1.1')
        self.assertEqual(act_item.code, '0.1.1.1')
        self.assign_result_to_cp_output(result, self.result_link.cp_output)
        result.refresh_from_db()
        activity.refresh_from_db()
        act_item.refresh_from_db()
        self.assertEqual(result.code, '1.2')
        self.assertEqual(activity.code, '1.2.1')
        self.assertEqual(act_item.code, '1.2.1.1')

    def test_associate_output_renumber_codes_shift_to_the_middle(self):
        self.assertEqual(self.result_link.code, '1')
        self.assertEqual(LowerResultFactory(code=None, result_link=self.result_link).code, '1.1')
        temp_link = InterventionResultLinkFactory(intervention=self.intervention, cp_output=None)
        r01 = LowerResultFactory(code=None, result_link=temp_link)
        r02 = LowerResultFactory(code=None, result_link=temp_link)

        new_result_link = InterventionResultLinkFactory(
            intervention=self.intervention,
            cp_output__result_type__name=ResultType.OUTPUT,
        )

        r21 = LowerResultFactory(code=None, result_link=new_result_link)
        self.assertEqual(r21.code, '2.1')

        self.assign_result_to_cp_output(r02, new_result_link.cp_output)
        # result link for r02 unchanged
        for obj in [r01, r02, r21, new_result_link]:
            obj.refresh_from_db()
        self.assertEqual(new_result_link.code, '2')
        self.assertEqual(r01.code, '0.1')
        self.assertEqual(r02.code, '2.1')
        self.assertEqual(r21.code, '2.2')

        self.assign_result_to_cp_output(r01, new_result_link.cp_output)
        # result link for r01 was removed, r21 as well as r02 shifted
        for obj in [r01, r02, r21, new_result_link]:
            obj.refresh_from_db()
        self.assertEqual(new_result_link.code, '2')
        self.assertEqual(r01.code, '2.1')
        self.assertEqual(r02.code, '2.2')
        self.assertEqual(r21.code, '2.3')

    def test_delete_pd_output_recalculate_broken_codes(self):
        LowerResultFactory(result_link=self.result_link, code='1.1')
        LowerResultFactory(result_link=self.result_link, code='2.1')
        LowerResultFactory(result_link=self.result_link, code='1.2')
        result = LowerResultFactory(result_link=self.result_link, code='1.3')
        response = self.forced_auth_req(
            'delete',
            reverse('partners:intervention-pd-output-detail', args=[self.intervention.pk, result.pk]),
            self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertListEqual(
            list(self.result_link.ll_results.order_by('id').values_list('code', flat=True)),
            ['1.1', '1.2', '1.3'],
        )

    def test_delete_pd_output_persist_temp_result_link(self):
        result_link = InterventionResultLinkFactory(intervention=self.intervention, cp_output=None)
        result = LowerResultFactory(result_link=result_link, code=None)
        second_result = LowerResultFactory(result_link=result_link, code=None)
        self.assertEqual(second_result.code, f'{result_link.code}.2')
        response = self.forced_auth_req(
            'delete',
            reverse('partners:intervention-pd-output-detail', args=[self.intervention.pk, result.pk]),
            self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data)
        self.assertTrue(InterventionResultLink.objects.filter(pk=result_link.pk).exists())
        second_result.refresh_from_db()
        self.assertEqual(second_result.code, f'{result_link.code}.1')

    def test_delete_pd_output_remove_temp_result_link(self):
        result_link = InterventionResultLinkFactory(intervention=self.intervention, cp_output=None)
        result = LowerResultFactory(result_link=result_link, code=None)
        response = self.forced_auth_req(
            'delete',
            reverse('partners:intervention-pd-output-detail', args=[self.intervention.pk, result.pk]),
            self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data)
        self.assertFalse(InterventionResultLink.objects.filter(pk=result_link.pk).exists())

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

    def test_create_intervention_snapshot(self):
        result = LowerResultFactory(result_link=self.result_link, name='old_name')
        response = self.forced_auth_req(
            'patch',
            reverse('partners:intervention-pd-output-detail', args=[self.intervention.pk, result.pk]),
            self.user,
            data={'name': 'new_name'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        activity = Activity.objects.first()
        self.assertEqual(activity.target, self.intervention)
        self.assertEqual(
            {'result_links': [{'ll_results': [{'name': {'after': 'new_name', 'before': 'old_name'}}]}]},
            activity.change,
        )
        self.assertIn(
            result.id,
            [lr['pk'] for lr in itertools.chain(*[rl['ll_results'] for rl in activity.data['result_links']])],
        )


class TestAppliedIndicatorsCreate(TestInterventionLowerResultsViewBase):
    def setUp(self):
        super().setUp()
        self.lower_result = LowerResultFactory(result_link=self.result_link)
        self.list_url = reverse('partners:intervention-indicators-list', args=[self.lower_result.pk])
        self.location = LocationFactory()
        self.intervention.flat_locations.add(self.location)
        self.intervention.sections.add(SectionFactory())
        self.create_data = {
            'indicator': {'title': "42", 'display_type': "number", 'unit': "number"},
            'locations': [self.location.pk],
            'section': self.intervention.sections.first().pk,
        }

    def test_create_unicef(self):
        response = self.forced_auth_req('post', self.list_url, self.user, data=self.create_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_create_unicef_partner_court(self):
        self.intervention.unicef_court = False
        self.intervention.save()
        response = self.forced_auth_req('post', self.list_url, self.user, data=self.create_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_create_partner_focal_point_unicef_court(self):
        response = self.forced_auth_req('post', self.list_url, self.partner_focal_point, data=self.create_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_create_partner_focal_point_partner_court(self):
        self.intervention.unicef_court = False
        self.intervention.save()
        response = self.forced_auth_req('post', self.list_url, self.partner_focal_point, data=self.create_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_create_partner_user(self):
        self.intervention.unicef_court = False
        self.intervention.save()
        response = self.forced_auth_req('post', self.list_url, self.partner_staff_member, data=self.create_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)


class TestAppliedIndicatorsUpdate(TestInterventionLowerResultsViewBase):
    def setUp(self):
        super().setUp()
        self.lower_result = LowerResultFactory(result_link=self.result_link)
        self.applied_indicator = AppliedIndicatorFactory(
            lower_result=self.lower_result,
            section=SectionFactory(),
        )
        self.applied_indicator.locations.add(LocationFactory())
        self.detail_url = reverse('partners:intervention-indicators-update', args=[self.applied_indicator.pk])
        self.intervention.flat_locations.add(self.applied_indicator.locations.first())
        self.intervention.sections.add(self.applied_indicator.section)

    def test_update_unicef(self):
        response = self.forced_auth_req('patch', self.detail_url, self.user, data={})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_update_unicef_partner_court(self):
        self.intervention.unicef_court = False
        self.intervention.save()
        response = self.forced_auth_req('patch', self.detail_url, self.user, data={})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_update_partner_focal_point_unicef_court(self):
        response = self.forced_auth_req('patch', self.detail_url, self.partner_focal_point, data={})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_update_partner_focal_point_partner_court(self):
        self.intervention.unicef_court = False
        self.intervention.save()
        response = self.forced_auth_req('patch', self.detail_url, self.partner_focal_point, data={})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_update_partner_user(self):
        self.intervention.unicef_court = False
        self.intervention.save()
        response = self.forced_auth_req('patch', self.detail_url, self.partner_staff_member, data={})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_destroy_unicef(self):
        response = self.forced_auth_req('delete', self.detail_url, self.user)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data)

    def test_destroy_after_draft(self):
        self.intervention.status = Intervention.SIGNED
        self.intervention.save()
        response = self.forced_auth_req('delete', self.detail_url, self.user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_destroy_unicef_partner_court(self):
        self.intervention.unicef_court = False
        self.intervention.save()
        response = self.forced_auth_req('delete', self.detail_url, self.user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_destroy_partner_focal_point_unicef_court(self):
        response = self.forced_auth_req('delete', self.detail_url, self.partner_focal_point)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_destroy_partner_focal_point_partner_court(self):
        self.intervention.unicef_court = False
        self.intervention.save()
        response = self.forced_auth_req('delete', self.detail_url, self.partner_focal_point)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data)

    def test_destroy_partner_user(self):
        self.intervention.unicef_court = False
        self.intervention.save()
        response = self.forced_auth_req('delete', self.detail_url, self.partner_staff_member)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)
