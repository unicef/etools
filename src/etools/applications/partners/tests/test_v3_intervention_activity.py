from datetime import date

from django.urls import reverse

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import Intervention
from etools.applications.partners.tests.factories import (
    InterventionFactory,
    InterventionResultLinkFactory,
    PartnerStaffFactory,
)
from etools.applications.reports.models import InterventionActivityItem, InterventionTimeFrame, ResultType
from etools.applications.reports.tests.factories import (
    InterventionActivityFactory,
    InterventionActivityItemFactory,
    LowerResultFactory,
)
from etools.applications.users.tests.factories import UserFactory


class BaseTestCase(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        self.user = UserFactory(is_staff=True, groups__data=['Partnership Manager', 'UNICEF User'])
        self.intervention = InterventionFactory(
            status=Intervention.DRAFT, unicef_court=True,
            start=date(year=1970, month=1, day=1),
            end=date(year=1970, month=12, day=31),
        )

        self.staff_member = PartnerStaffFactory(partner=self.intervention.agreement.partner)
        self.partner_focal_point = UserFactory(groups__data=[], profile__partner_staff_member=self.staff_member.id)
        self.intervention.partner_focal_points.add(self.staff_member)

        self.result_link = InterventionResultLinkFactory(
            intervention=self.intervention,
            cp_output__result_type__name=ResultType.OUTPUT,
        )
        self.pd_output = LowerResultFactory(result_link=self.result_link)

        self.activity = InterventionActivityFactory(result=self.pd_output)
        self.list_url = reverse(
            'partners:intervention-activity-list',
            args=[self.intervention.pk, self.pd_output.pk]
        )
        self.detail_url = reverse(
            'partners:intervention-activity-detail',
            args=[self.intervention.pk, self.pd_output.pk, self.activity.pk]
        )


class TestFunctionality(BaseTestCase):
    def test_set_cash_values_directly(self):
        response = self.forced_auth_req(
            'patch', self.detail_url,
            user=self.user,
            data={
                'unicef_cash': 1,
                'cso_cash': 2,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['unicef_cash'], '1.00')
        self.assertEqual(response.data['cso_cash'], '2.00')
        self.assertEqual(response.data['partner_percentage'], '66.67')

    def test_set_cash_values_from_items(self):
        InterventionActivityItemFactory(activity=self.activity, unicef_cash=8)
        response = self.forced_auth_req(
            'patch', self.detail_url,
            user=self.user,
            data={
                'items': [
                    {
                        'name': 'first_item',
                        'unicef_cash': '3.0', 'cso_cash': '4.0',
                    },
                    {
                        'name': 'second_item',
                        'unicef_cash': '0.0', 'cso_cash': '2.0',
                    }
                ],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['unicef_cash'], '3.00')
        self.assertEqual(response.data['cso_cash'], '6.00')
        self.assertEqual(response.data['partner_percentage'], '66.67')

    def test_set_items(self):
        item_to_remove = InterventionActivityItemFactory(activity=self.activity)
        item_to_update = InterventionActivityItemFactory(activity=self.activity, name='old')
        self.assertEqual(self.activity.items.count(), 2)

        response = self.forced_auth_req(
            'patch', self.detail_url,
            user=self.user,
            data={
                'items': [
                    {'id': item_to_update.id, 'name': 'new'},
                    {
                        'name': 'first_item',
                        'unicef_cash': '1.0', 'cso_cash': '2.0',
                    }
                ],
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(self.activity.items.count(), 2)
        self.assertEqual(len(response.data['items']), 2)
        self.assertEqual(InterventionActivityItem.objects.filter(id=item_to_remove.id).exists(), False)

    def test_set_time_frames(self):
        item_to_remove = InterventionTimeFrame.objects.get(
            intervention=self.intervention,
            start_date=date(year=1970, month=10, day=1),
            end_date=date(year=1970, month=12, day=31)
        )
        item_to_keep = InterventionTimeFrame.objects.get(
            intervention=self.intervention,
            start_date=date(year=1970, month=4, day=1),
            end_date=date(year=1970, month=7, day=1)
        )
        self.activity.time_frames.add(item_to_keep, item_to_remove)

        response = self.forced_auth_req(
            'patch', self.detail_url,
            user=self.user,
            data={
                'time_frames': [
                    {'enabled': False},
                    {'enabled': True},
                    {'enabled': True},
                    {'enabled': False},
                ],
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(len(response.data['time_frames']), 4)
        self.assertEqual(self.activity.time_frames.count(), 2)
        self.assertEqual(self.activity.time_frames.filter(pk=item_to_remove.pk).exists(), False)
        self.assertEqual(self.activity.time_frames.filter(pk=item_to_keep.pk).exists(), True)
        self.assertEqual([t['enabled'] for t in response.data['time_frames']], [False, True, True, False])

    def test_minimal_create(self):
        response = self.forced_auth_req(
            'post', self.list_url,
            user=self.user,
            data={'name': 'test'}
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertIn('intervention', response.data)

    def test_destroy(self):
        response = self.forced_auth_req('delete', self.detail_url, user=self.user, data={})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data)

    def test_update(self):
        response = self.forced_auth_req('patch', self.detail_url, user=self.user, data={'name': 'new'})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['name'], 'new')
        self.assertIn('intervention', response.data)

    def test_list(self):
        response = self.forced_auth_req('get', self.list_url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED, response.data)

    def test_retrieve(self):
        response = self.forced_auth_req('get', self.detail_url, user=self.user)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertNotIn('intervention', response.data)

    def test_time_frames_presented_in_details(self):
        self.intervention.quarters.first().activities.add(self.activity)
        response = self.forced_auth_req(
            'get',
            reverse('pmp_v3:intervention-detail', args=[self.intervention.id]),
            user=self.user,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['result_links'][0]['ll_results'][0]['activities'][0]['time_frames'][0]['name'],
            'Q1'
        )


class TestPermissions(BaseTestCase):
    def test_create_for_unknown_user(self):
        response = self.forced_auth_req('post', self.list_url, UserFactory(groups__data=[]), data={})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_create_for_signed_intervention(self):
        self.intervention.status = Intervention.SIGNED
        self.intervention.save()

        response = self.forced_auth_req('post', self.list_url, self.user, data={})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_create_assigned_partner_user_unicef_court(self):
        response = self.forced_auth_req('post', self.list_url, self.partner_focal_point, data={})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_create_assigned_partner_user_partner_court(self):
        self.intervention.unicef_court = False
        self.intervention.save()

        response = self.forced_auth_req(
            'post', self.list_url, self.partner_focal_point,
            data={'name': 'test', 'context_details': 'some important comment'}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_create_assigned_partner_user_signed_intervention(self):
        self.intervention.unicef_court = False
        self.intervention.status = Intervention.SIGNED
        self.intervention.save()

        response = self.forced_auth_req('post', self.list_url, self.partner_focal_point, data={})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_create_unassigned_partner_user(self):
        self.intervention.unicef_court = False
        self.intervention.partner_focal_points.clear()
        self.intervention.save()

        response = self.forced_auth_req('post', self.list_url, self.partner_focal_point, data={})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)
