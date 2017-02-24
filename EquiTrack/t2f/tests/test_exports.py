from __future__ import unicode_literals

import csv
import logging
from cStringIO import StringIO

from django.core.urlresolvers import reverse

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase
from t2f.models import make_travel_reference_number

from .factories import TravelFactory

log = logging.getLogger('__name__')


class TravelExports(APITenantTestCase):
    def setUp(self):
        super(TravelExports, self).setUp()
        self.traveler = UserFactory()
        self.unicef_staff = UserFactory(is_staff=True)
        self.travel = TravelFactory(reference_number=make_travel_reference_number(),
                                    traveler=self.traveler,
                                    supervisor=self.unicef_staff)

    def test_urls(self):
        export_url = reverse('t2f:travels:list:export')
        self.assertEqual(export_url, '/api/t2f/travels/export/')

        export_url = reverse('t2f:travels:list:finance_export')
        self.assertEqual(export_url, '/api/t2f/travels/finance-export/')

        export_url = reverse('t2f:travels:list:travel_admin_export')
        self.assertEqual(export_url, '/api/t2f/travels/travel-admin-export/')

        export_url = reverse('t2f:travels:list:invoice_export')
        self.assertEqual(export_url, '/api/t2f/travels/invoice-export/')

    def test_export(self):
        response = self.forced_auth_req('get', reverse('t2f:travels:list:export'),
                                        user=self.unicef_staff)
        export_csv = csv.reader(StringIO(response.content))

        # check header
        self.assertEqual(export_csv.next(),
                         ['id',
                          'reference_number',
                          'traveler',
                          'purpose',
                          'start_date',
                          'end_date',
                          'status',
                          'created',
                          'section',
                          'office',
                          'supervisor',
                          'ta_required',
                          'ta_reference_number',
                          'approval_date',
                          'is_driver',
                          'attachment_count'])

    def test_finance_export(self):
        response = self.forced_auth_req('get', reverse('t2f:travels:list:finance_export'),
                                        user=self.unicef_staff)
        export_csv = csv.reader(StringIO(response.content))

        # check header
        self.assertEqual(export_csv.next(),
                         ['reference_number',
                          'traveler',
                          'office',
                          'section',
                          'status',
                          'supervisor',
                          'start_date',
                          'end_date',
                          'purpose_of_travel',
                          'mode_of_travel',
                          'international_travel',
                          'require_ta',
                          'dsa_total',
                          'expense_total',
                          'deductions_total'])

    def test_travel_admin_export(self):
        response = self.forced_auth_req('get', reverse('t2f:travels:list:travel_admin_export'),
                                        user=self.unicef_staff)
        export_csv = csv.reader(StringIO(response.content))

        # check header
        self.assertEqual(export_csv.next(),
                         ['reference_number',
                          'traveler',
                          'office',
                          'section',
                          'status',
                          'origin',
                          'destination',
                          'departure_time',
                          'arrival_time',
                          'dsa_area',
                          'overnight_travel',
                          'mode_of_travel',
                          'airline'])

    def test_invoice_export(self):
        response = self.forced_auth_req('get', reverse('t2f:travels:list:invoice_export'),
                                        user=self.unicef_staff)
        export_csv = csv.reader(StringIO(response.content))

        # check header
        self.assertEqual(export_csv.next(),
                         ['reference_number',
                          'ta_number',
                          'vendor_number',
                          'currency',
                          'amount',
                          'status',
                          'message',
                          'vision_fi_doc',
                          'wbs',
                          'grant',
                          'fund'])
