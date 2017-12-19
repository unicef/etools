from __future__ import unicode_literals

import json

from django.core.urlresolvers import reverse

from EquiTrack.tests.mixins import APITenantTestCase
from publics.models import EPOCH_ZERO, TravelExpenseType
from publics.tests.factories import PublicsAirlineCompanyFactory, PublicsTravelExpenseTypeFactory
from users.tests.factories import UserFactory


class GhostData(APITenantTestCase):
    def setUp(self):
        super(GhostData, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)

    def test_urls(self):
        static_data_url = reverse('public:missing_static')
        self.assertEqual(static_data_url, '/api/static_data/missing/')

        currencies_url = reverse('public:missing_currencies')
        self.assertEqual(currencies_url, '/api/currencies/missing/')

        dsa_regions_url = reverse('public:missing_dsa_regions')
        self.assertEqual(dsa_regions_url, '/api/dsa_regions/missing/')

        business_areas_url = reverse('public:missing_business_areas')
        self.assertEqual(business_areas_url, '/api/business_areas/missing/')

        expense_types_url = reverse('public:missing_expense_types')
        self.assertEqual(expense_types_url, '/api/expense_types/missing/')

        airlines_url = reverse('public:missing_airlines')
        self.assertEqual(airlines_url, '/api/airlines/missing/')

    def test_on_instance_delete(self):
        expense_type = PublicsTravelExpenseTypeFactory()

        self.assertEqual(expense_type.deleted_at, EPOCH_ZERO)

        expense_type.delete()
        self.assertNotEqual(expense_type.deleted_at, EPOCH_ZERO)

    def test_queryset_delete(self):
        PublicsTravelExpenseTypeFactory()
        PublicsTravelExpenseTypeFactory()
        PublicsTravelExpenseTypeFactory()

        total_expense_type_count = TravelExpenseType.objects.all().count()
        self.assertEqual(total_expense_type_count, 3)

        deleted_at_epoch_zero_count = TravelExpenseType.objects.filter(deleted_at=EPOCH_ZERO).count()
        self.assertEqual(deleted_at_epoch_zero_count, 3)

        deleted_at_populated_count = TravelExpenseType.objects.exclude(deleted_at=EPOCH_ZERO).count()
        self.assertEqual(deleted_at_populated_count, 0)

        TravelExpenseType.objects.all().delete()

        deleted_at_epoch_zero_count = TravelExpenseType.objects.filter(deleted_at=EPOCH_ZERO).count()
        self.assertEqual(deleted_at_epoch_zero_count, 0)

        deleted_at_populated_count = TravelExpenseType.admin_objects.exclude(deleted_at=EPOCH_ZERO).count()
        self.assertEqual(deleted_at_populated_count, 3)

    def test_single_endpoint(self):
        expense_type = PublicsTravelExpenseTypeFactory()

        response = self.forced_auth_req('get', reverse('public:expense_types'),
                                        user=self.unicef_staff)

        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json), 1)

        expense_type.delete()

        response = self.forced_auth_req('get', reverse('public:expense_types'),
                                        user=self.unicef_staff)

        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json), 0)

        response = self.forced_auth_req('get', reverse('public:missing_expense_types'),
                                        user=self.unicef_staff)
        self.assertEqual(response.status_code, 400)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json,
                         {'values': ['This list may not be empty.']})

        response = self.forced_auth_req('get', reverse('public:missing_expense_types'),
                                        data={'values': [expense_type.pk]},
                                        user=self.unicef_staff)
        self.assertEqual(response.status_code, 200)

    def test_multiendpoint(self):
        airline = PublicsAirlineCompanyFactory()

        response = self.forced_auth_req('get', reverse('public:static'),
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json['airlines']), 1)

        airline.delete()

        response = self.forced_auth_req('get', reverse('public:static'),
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json['airlines']), 0)

        response = self.forced_auth_req('get', reverse('public:missing_static'),
                                        data={'values': [airline.pk]},
                                        user=self.unicef_staff)
        self.assertEqual(response.status_code, 400)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json,
                         {'category': ['This field is required.']})

        response = self.forced_auth_req('get', reverse('public:missing_static'),
                                        data={'values': [airline.pk],
                                              'category': 'airlines'},
                                        user=self.unicef_staff)
        self.assertEqual(response.status_code, 200)
