from datetime import date

from django.urls import reverse

from rest_framework import status

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import Intervention
from etools.applications.partners.permissions import PARTNERSHIP_MANAGER_GROUP, UNICEF_USER
from etools.applications.partners.tests.factories import (
    InterventionAmendmentFactory,
    InterventionFactory,
    InterventionResultLinkFactory,
)
from etools.applications.reports.models import InterventionActivityItem, InterventionTimeFrame, ResultType
from etools.applications.reports.tests.factories import (
    InterventionActivityFactory,
    InterventionActivityItemFactory,
    LowerResultFactory,
)
from etools.applications.users.tests.factories import UserFactory
from etools.libraries.tests.db_utils import CaptureQueries


class BaseTestCase(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        self.user = UserFactory(is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP])
        self.intervention = InterventionFactory(
            status=Intervention.DRAFT, unicef_court=True,
            start=date(year=1970, month=1, day=1),
            end=date(year=1970, month=12, day=31),
        )
        self.partner_focal_point = UserFactory(
            realms__data=['IP Viewer'],
            profile__organization=self.intervention.agreement.partner.organization
        )
        self.intervention.partner_focal_points.add(self.partner_focal_point)
        self.intervention.unicef_focal_points.add(self.user)

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
        self.intervention.refresh_from_db()
        budget_response = response.data["intervention"]["planned_budget"]
        self.assertEqual(
            budget_response["total_cash_local"],
            str(self.intervention.planned_budget.total_cash_local()),
        )

    def test_set_unfunded_cash_when_pd_funded(self):
        self.assertFalse(self.intervention.planned_budget.has_unfunded_cash)
        response = self.forced_auth_req(
            'patch', self.detail_url,
            user=self.user,
            data={
                'unicef_cash': 1,
                'cso_cash': 2,
                'unfunded_cash': 1
            }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_set_unfunded_cash_when_pd_unfunded(self):
        self.intervention.planned_budget.has_unfunded_cash = True
        self.intervention.planned_budget.save()
        response = self.forced_auth_req(
            'patch', self.detail_url,
            user=self.user,
            data={
                'unicef_cash': 1,
                'cso_cash': 2,
                'unfunded_cash': 1
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['unicef_cash'], '1.00')
        self.assertEqual(response.data['cso_cash'], '2.00')
        self.assertEqual(response.data['unfunded_cash'], '1.00')
        self.assertEqual(response.data['partner_percentage'], '50.00')
        self.intervention.refresh_from_db()
        budget_response = response.data["intervention"]["planned_budget"]
        self.assertEqual(
            budget_response["total_cash_local"],
            str(self.intervention.planned_budget.total_cash_local()),
        )

    def test_set_cash_values_from_items(self):
        InterventionActivityItemFactory(activity=self.activity, unicef_cash=8)
        response = self.forced_auth_req(
            'patch', self.detail_url,
            user=self.user,
            data={
                'items': [
                    {
                        'name': 'first_item',
                        'unit': 'item', 'no_units': 1, 'unit_price': '7.0',
                        'unicef_cash': '3.0', 'cso_cash': '4.0',
                    },
                    {
                        'name': 'second_item',
                        'unit': 'item', 'no_units': 1, 'unit_price': '2.0',
                        'unicef_cash': '0.0', 'cso_cash': '2.0',
                    },
                    {
                        'name': 'third_item',
                        'unit': 'item', 'no_units': '0.1', 'unit_price': '2.0',
                        'unicef_cash': '0.0', 'cso_cash': '0.2',
                    }
                ],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['unicef_cash'], '3.00')
        self.assertEqual(response.data['cso_cash'], '6.20')
        self.assertEqual(response.data['partner_percentage'], '67.39')  # cso_cash / (unicef_cash + cso_cash)

    def test_set_bad_cash_values_having_items(self):
        InterventionActivityItemFactory(activity=self.activity, unicef_cash=8, cso_cash=5)
        self.activity.update_cash()
        response = self.forced_auth_req(
            'patch', self.detail_url,
            user=self.user,
            data={
                'unicef_cash': 1,
                'cso_cash': 1,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['unicef_cash'], '8.00')
        self.assertEqual(response.data['cso_cash'], '5.00')

    def test_set_cash_values_having_no_items(self):
        response = self.forced_auth_req(
            'patch', self.detail_url,
            user=self.user,
            data={
                'unicef_cash': 1,
                'cso_cash': 1,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['unicef_cash'], '1.00')
        self.assertEqual(response.data['cso_cash'], '1.00')

    def test_set_items(self):
        item_to_remove = InterventionActivityItemFactory(
            activity=self.activity,
            no_units=1, unit_price=42, unicef_cash=22, cso_cash=20,
        )
        item_to_update = InterventionActivityItemFactory(
            activity=self.activity,
            no_units=1, unit_price=42, unicef_cash=22, cso_cash=20,
            name='old',
        )
        self.assertEqual(self.activity.items.count(), 2)

        response = self.forced_auth_req(
            'patch', self.detail_url,
            user=self.user,
            data={
                'items': [
                    {'id': item_to_update.id, 'name': 'new'},
                    {
                        'name': 'first_item',
                        'unit': 'item', 'no_units': 1, 'unit_price': '3.0',
                        'unicef_cash': '1.0', 'cso_cash': '2.0',
                    }
                ],
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(self.activity.items.count(), 2)
        self.assertEqual(len(response.data['items']), 2)
        self.assertEqual(response.data['items'][0]['name'], 'new')
        self.assertEqual(InterventionActivityItem.objects.filter(id=item_to_remove.id).exists(), False)

    def test_set_items_validate_bad_id(self):
        valid_item_to_update = InterventionActivityItemFactory(activity=self.activity)
        invalid_item_to_update = InterventionActivityItemFactory(activity__result=self.activity.result)

        response = self.forced_auth_req(
            'patch', self.detail_url,
            user=self.user,
            data={
                'items': [
                    {
                        'id': valid_item_to_update.id, 'name': 'first_item',
                        'unit': 'item', 'no_units': 1, 'unit_price': '3.0',
                        'unicef_cash': '1.0', 'cso_cash': '2.0',
                    },
                    {
                        'id': invalid_item_to_update.id, 'name': 'second_item',
                        'unit': 'item', 'no_units': 1, 'unit_price': '3.0',
                        'unicef_cash': '1.0', 'cso_cash': '2.0',
                    },
                ],
            }
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertEqual({}, response.data['items'][0])
        self.assertIn('Unable to find item', response.data['items'][1]['non_field_errors'][0])

    def test_set_many_items_queries(self):
        items = [
            InterventionActivityItem(
                activity=self.activity, name=str(i), unit='test',
                no_units=1, unit_price=42, unicef_cash=22, cso_cash=20,
            )
            for i in range(100)
        ]
        InterventionActivityItem.objects.bulk_create(items)
        self.activity.update_cash()

        with CaptureQueries() as cq:
            response = self.forced_auth_req(
                'patch', self.detail_url,
                user=self.user,
                data={
                    'is_active': True,
                    'items': [
                        {
                            'id': item.id, 'name': item.name,
                            'unit': item.unit, 'no_units': str(item.no_units), 'unit_price': str(item.unit_price),
                            'unicef_cash': str(item.unicef_cash), 'cso_cash': str(item.cso_cash),
                        }
                        for item in items
                    ],
                }
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        # initially there were around 2k db queries, so ~200 is more or less fine.
        # they are mostly caused by snapshot + heavy permissions
        self.assertLess(len(cq.queries), 200, '\n'.join((f'{i}: {q["sql"]}' for i, q in enumerate(cq.queries))))

    def test_remove_all_items(self):
        items = [
            InterventionActivityItem(
                activity=self.activity, name=str(i), unit='test',
                no_units=1, unit_price=42, unicef_cash=22, cso_cash=20,
            )
            for i in range(5)
        ]
        InterventionActivityItem.objects.bulk_create(items)
        self.assertEqual(self.activity.items.count(), 5)

        response = self.forced_auth_req(
            'patch', self.detail_url,
            user=self.user,
            data={
                'items': [],
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(self.activity.items.count(), 0)
        self.assertEqual(len(response.data['items']), 0)

    def test_budget_validation(self):
        item_to_update = InterventionActivityItemFactory(
            activity=self.activity,
            no_units=1, unit_price=42, unicef_cash=22, cso_cash=20,
        )

        response = self.forced_auth_req(
            'patch', self.detail_url,
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

    def test_budget_item_validation_rounding_ok(self):
        item_to_update = InterventionActivityItemFactory(activity=self.activity)

        response = self.forced_auth_req(
            'patch', self.detail_url,
            user=self.user,
            data={
                'items': [{
                    'id': item_to_update.id,
                    'no_units': '17.22',
                    'unit_price': '17.89',
                    'cso_cash': '287.00',
                    'unicef_cash': '21.06',
                }],
            }
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

    def test_set_time_frames(self):
        item_to_remove = InterventionTimeFrame.objects.get(
            intervention=self.intervention,
            start_date=date(year=1970, month=10, day=1),
            end_date=date(year=1970, month=12, day=31)
        )
        item_to_keep = InterventionTimeFrame.objects.get(
            intervention=self.intervention,
            start_date=date(year=1970, month=4, day=1),
            end_date=date(year=1970, month=6, day=30)
        )
        self.activity.time_frames.add(item_to_keep, item_to_remove)
        time_frames = [q.id for q in self.intervention.quarters.all()[1:3]]

        response = self.forced_auth_req(
            'patch', self.detail_url,
            user=self.user,
            data={'time_frames': time_frames},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(len(response.data['time_frames']), 2)
        self.assertEqual(self.activity.time_frames.count(), 2)
        self.assertEqual(self.activity.time_frames.filter(pk=item_to_remove.pk).exists(), False)
        self.assertEqual(self.activity.time_frames.filter(pk=item_to_keep.pk).exists(), True)
        self.assertEqual(response.data['time_frames'], time_frames)

    def test_set_multiple_items_unique_codes(self):
        response = self.forced_auth_req(
            'patch', self.detail_url,
            user=self.user,
            data={
                'items': [
                    {
                        'name': f'item_{i}',
                        'unit': 'item', 'no_units': 1, 'unit_price': '1',
                        'unicef_cash': '1', 'cso_cash': '0.0',
                    } for i in range(3)
                ],
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertListEqual(
            list(self.activity.items.order_by('code').values_list('code', flat=True)),
            [self.activity.code + f'.{i + 1}' for i in range(3)]
        )

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

    def test_destroy_after_develop(self):
        self.intervention.status = Intervention.SIGNED
        self.intervention.save()
        response = self.forced_auth_req('delete', self.detail_url, user=self.user, data={})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_destroy_in_amendment(self):
        self.intervention.status = Intervention.SIGNED
        self.intervention.save()
        response = self.forced_auth_req('delete', self.detail_url, user=self.user, data={})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_destroy_in_amendment_original_activity(self):
        amendment = InterventionAmendmentFactory(intervention=self.intervention)
        intervention = amendment.amended_intervention
        pd_output = intervention.result_links.first().ll_results.first()
        activity = amendment.amended_intervention.result_links.first().ll_results.first().activities.first()
        response = self.forced_auth_req(
            'delete',
            reverse(
                'partners:intervention-activity-detail',
                args=[intervention.pk, pd_output.pk, activity.pk]
            ),
            user=self.user,
            data={}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_destroy_in_amendment_new_activity(self):
        amendment = InterventionAmendmentFactory(intervention=self.intervention)
        intervention = amendment.amended_intervention
        pd_output = intervention.result_links.first().ll_results.first()
        activity = InterventionActivityFactory(result=amendment.amended_intervention.result_links.first().ll_results.first())
        response = self.forced_auth_req(
            'delete',
            reverse(
                'partners:intervention-activity-detail',
                args=[intervention.pk, pd_output.pk, activity.pk]
            ),
            user=self.user,
            data={}
        )
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
        self.assertIn('time_frames', response.data['result_links'][0]['ll_results'][0]['activities'][0])

    def test_ordering_preserved_on_edit(self):
        second_activity = InterventionActivityFactory(result=self.pd_output)

        def check_ordering():
            details_response = self.forced_auth_req(
                'get',
                reverse('pmp_v3:intervention-detail', args=[self.intervention.id]),
                user=self.user,
            )
            self.assertEqual(details_response.status_code, status.HTTP_200_OK)
            self.assertListEqual(
                [a['id'] for a in details_response.data['result_links'][0]['ll_results'][0]['activities']],
                [self.activity.id, second_activity.id]
            )

        check_ordering()

        response = self.forced_auth_req(
            'patch', self.detail_url,
            user=self.user,
            data={'context_details': 'test'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        check_ordering()

    def test_create_items_fractional_total(self):
        response = self.forced_auth_req(
            'post', self.list_url,
            user=self.user,
            data={
                'name': 'test',
                'items': [{
                    'name': 'test',
                    'unit': 'test',
                    'no_units': 17.9,
                    'unit_price': 14.89,
                    'unicef_cash': 4.64,
                    'cso_cash': 261.89
                }]
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def test_deactivate_activity(self):
        response = self.forced_auth_req(
            'patch', self.detail_url,
            user=self.user,
            data={
                'is_active': False,
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['is_active'], False)


class TestPermissions(BaseTestCase):
    def test_create_for_unknown_user(self):
        response = self.forced_auth_req('post', self.list_url, UserFactory(realms__data=[]), data={})
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

    def test_create_in_amendment(self):
        self.intervention.unicef_court = False
        self.intervention.in_amendment = True
        self.intervention.save()

        response = self.forced_auth_req(
            'post', self.list_url, self.user,
            data={'name': 'test', 'context_details': 'test'}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
