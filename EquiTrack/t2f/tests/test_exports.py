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
        # TODO figure out date comparison and unicode vs str
        line = export_csv.next()
        self.assertEqual(line, [
                str(self.travel.id),
                str(self.travel.reference_number),
                str(self.traveler.get_full_name()),
                str(self.travel.purpose),
                line[4],
                line[5],
                str(self.travel.status),
                line[7],
                str(self.travel.section.name),
                str(self.travel.office.name),
                str(self.travel.supervisor.id),
                str(self.travel.check_ta_required()),
                str(self.travel.reference_number),
                line[13],
                str(self.travel.is_driver),
                str(self.travel.attachments.count()),
            ]
        )

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
        # TODO figure out date comparison and unicode vs str
        line = export_csv.next()
        self.assertEqual(line, [
                str(self.travel.reference_number),
                str(self.traveler.get_full_name()),
                str(self.travel.office.name),
                str(self.travel.section.name),
                str(self.travel.status),
                str(self.travel.supervisor.get_full_name()),
                line[6],
                line[7],
                str(self.travel.purpose),
                ', '.join(self.travel.mode_of_travel),
                str(self.travel.international_travel),
                str(self.travel.ta_required),
                '{:.10f}'.format(self.travel.cost_summary["dsa_total"]),
                '{:.10f}'.format(self.travel.cost_summary["expenses_total"]),
                '{:.10f}'.format(self.travel.cost_summary["deductions_total"]),
            ]
        )

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
        # TODO figure out date comparison and unicode vs str
        line = export_csv.next()
        self.assertEqual(line, [
                str(self.travel.reference_number),
                str(self.traveler.get_full_name()),
                str(self.travel.office.name),
                str(self.travel.section.name),
                str(self.travel.status),
                str(self.travel.itinerary.first().origin),
                str(self.travel.itinerary.first().destination),
                # str(self.travel.itinerary.first().departure_date),
                # str(self.travel.itinerary.first().arrival_date),
                line[7],
                line[8],
                str(self.travel.itinerary.first().dsa_region.area_code),
                str(self.travel.itinerary.first().overnight_travel),
                str(self.travel.itinerary.first().mode_of_travel),
                '',
            ]
        )

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
