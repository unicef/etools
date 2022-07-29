import csv
import datetime
import logging
from io import StringIO

from django.urls import reverse

from pytz import UTC
from unicef_locations.tests.factories import LocationFactory

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners.tests.factories import InterventionFactory
from etools.applications.publics.tests.factories import (
    PublicsAirlineCompanyFactory,
    PublicsDSARateFactory,
    PublicsDSARegionFactory,
)
from etools.applications.reports.tests.factories import OfficeFactory, ResultFactory, SectionFactory
from etools.applications.t2f.models import ModeOfTravel, TravelActivity, TravelType
from etools.applications.t2f.tests.factories import (
    ItineraryItemFactory,
    TravelActivityFactory,
    TravelAttachmentFactory,
    TravelFactory,
)
from etools.applications.users.tests.factories import UserFactory

log = logging.getLogger('__name__')


class TravelExports(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.traveler = UserFactory(first_name='John', last_name='Doe')
        cls.unicef_staff = UserFactory(
            first_name='Jakab', last_name='Gipsz', is_staff=True)

    def test_urls(self):
        export_url = reverse('t2f:travels:list:activity_export')
        self.assertEqual(export_url, '/api/t2f/travels/export/')

        export_url = reverse('t2f:travels:list:travel_admin_export')
        self.assertEqual(export_url, '/api/t2f/travels/travel-admin-export/')

    def test_activity_export(self):
        office = OfficeFactory(name='Budapest')
        section_health = SectionFactory(name='Health')
        section_education = SectionFactory(name='Education')

        location_ABC = LocationFactory(name='Location ABC')
        location_345 = LocationFactory(name='Location 345')
        location_111 = LocationFactory(name='Location 111')

        partnership_A1 = InterventionFactory(title='Partnership A1')
        partner = partnership_A1.agreement.partner
        partner.organization.name = 'Partner A'
        partner.organization.save()

        partnership_A2 = InterventionFactory(title='Partnership A2')
        agreement = partnership_A2.agreement
        agreement.partner = partner
        agreement.save()

        partnership_B3 = InterventionFactory(title='Partnership B3')
        partner = partnership_B3.agreement.partner
        partner.organization.name = 'Partner B'
        partner.organization.save()

        partnership_C1 = InterventionFactory(title='Partnership C1')
        partner = partnership_C1.agreement.partner
        partner.organization.name = 'Partner C'
        partner.organization.save()

        # Some results
        result_A11 = ResultFactory(name='Result A11')
        result_A21 = ResultFactory(name='Result A21')

        # set up travels
        user_joe_smith = UserFactory(first_name='Joe',
                                     last_name='Smith')
        user_alice_carter = UserFactory(first_name='Alice',
                                        last_name='Carter')
        user_lenox_lewis = UserFactory(first_name='Lenox',
                                       last_name='Lewis')
        supervisor = UserFactory(first_name='ImYour',
                                 last_name='Supervisor')

        travel_1 = TravelFactory(reference_number='2016/1000',
                                 traveler=user_joe_smith,
                                 purpose='Workshop',
                                 office=office,
                                 supervisor=supervisor,
                                 section=section_health,
                                 start_date=datetime.date(2017, 11, 8),
                                 end_date=datetime.date(2017, 11, 14),
                                 )
        travel_2 = TravelFactory(reference_number='2016/1211',
                                 supervisor=supervisor,
                                 traveler=user_alice_carter,
                                 purpose='Mission',
                                 office=office,
                                 section=section_education,
                                 start_date=datetime.date(2017, 11, 8),
                                 end_date=datetime.date(2017, 11, 14),
                                 )

        # Do some cleanup
        TravelActivity.objects.all().delete()

        # Create the activities finally
        activity_1 = TravelActivityFactory(travel_type=TravelType.PROGRAMME_MONITORING,
                                           date=datetime.datetime(
                                               2016, 12, 3, tzinfo=UTC),
                                           result=result_A11,
                                           primary_traveler=user_joe_smith)
        activity_1.travels.add(travel_1)
        activity_1.locations.set([location_ABC, location_345])
        activity_1.partner = partnership_A1.agreement.partner
        activity_1.partnership = partnership_A1
        activity_1.save()

        activity_2 = TravelActivityFactory(travel_type=TravelType.PROGRAMME_MONITORING,
                                           date=datetime.datetime(
                                               2016, 12, 4, tzinfo=UTC),
                                           result=result_A21,
                                           primary_traveler=user_lenox_lewis)
        activity_2.travels.add(travel_1)
        activity_2.locations.set([location_111])
        activity_2.partner = partnership_A2.agreement.partner
        activity_2.partnership = partnership_A2
        activity_2.save()

        activity_3 = TravelActivityFactory(travel_type=TravelType.MEETING,
                                           date=datetime.datetime(
                                               2016, 12, 3, tzinfo=UTC),
                                           result=None,
                                           primary_traveler=user_joe_smith)
        activity_3.travels.add(travel_1)
        activity_3.locations.set([location_ABC])
        activity_3.partner = partnership_B3.agreement.partner
        activity_3.partnership = partnership_B3
        activity_3.save()

        activity_4 = TravelActivityFactory(travel_type=TravelType.SPOT_CHECK,
                                           date=datetime.datetime(
                                               2016, 12, 6, tzinfo=UTC),
                                           result=None,
                                           primary_traveler=user_alice_carter)
        activity_4.travels.add(travel_2)
        activity_4.locations.set([location_111, location_345])
        activity_4.partner = partnership_C1.agreement.partner
        activity_4.partnership = partnership_C1
        activity_4.save()
        TravelAttachmentFactory(
            file="test_file.pdf",
            travel=activity_4.travel,
            type="HACT Programme Monitoring Report",
        )

        with self.assertNumQueries(11):
            response = self.forced_auth_req('get', reverse('t2f:travels:list:activity_export'),
                                            user=self.unicef_staff)
        export_csv = csv.reader(StringIO(response.content.decode('utf-8')))
        rows = [r for r in export_csv]

        self.assertEqual(len(rows), 5)
        # check header
        self.assertEqual(rows[0], [
            'reference_number',
            'traveler',
            'purpose',
            'office',
            'section',
            'status',
            'supervisor',
            'trip_type',
            'partner',
            'partnership',
            'pd_reference',
            'results',
            'locations',
            'start_date',
            'end_date',
            'is_secondary_traveler',
            'primary_traveler_name',
            'hact_visit_report',
        ])

        self.assertEqual(rows[1], [
            '2016/1000',
            'Joe Smith',
            'Workshop',
            'Budapest',
            'Health',
            'planned',
            'ImYour Supervisor',
            'Programmatic Visit',
            'Partner A',
            'Partnership A1',
            partnership_A1.number,
            'Result A11',
            'Location ABC, Location 345',
            '08-Nov-2017',
            '14-Nov-2017',
            '',
            '',
            '',
        ])

        self.assertEqual(rows[2], [
            '2016/1000',
            'Joe Smith',
            'Workshop',
            'Budapest',
            'Health',
            'planned',
            'ImYour Supervisor',
            'Programmatic Visit',
            'Partner A',
            'Partnership A2',
            partnership_A2.number,
            'Result A21',
            'Location 111',
            '08-Nov-2017',
            '14-Nov-2017',
            'YES',
            'Lenox Lewis',
            '',
        ])

        self.assertEqual(rows[3], [
            '2016/1000',
            'Joe Smith',
            'Workshop',
            'Budapest',
            'Health',
            'planned',
            'ImYour Supervisor',
            'Meeting',
            'Partner B',
            'Partnership B3',
            partnership_B3.number,
            '',
            'Location ABC',
            '08-Nov-2017',
            '14-Nov-2017',
            '',
            '',
            '',
        ])

        self.assertEqual(rows[4], [
            '2016/1211',
            'Alice Carter',
            'Mission',
            'Budapest',
            'Education',
            'planned',
            'ImYour Supervisor',
            'Spot Check',
            'Partner C',
            'Partnership C1',
            partnership_C1.number,
            '',
            'Location 345, Location 111',
            '08-Nov-2017',
            '14-Nov-2017',
            '',
            '',
            'Yes',
        ])

    def test_travel_admin_export(self):
        dsa_brd = PublicsDSARegionFactory(area_code='BRD')
        PublicsDSARateFactory(region=dsa_brd)
        dsa_lan = PublicsDSARegionFactory(area_code='LAN')
        PublicsDSARateFactory(region=dsa_lan)

        airline_jetstar = PublicsAirlineCompanyFactory(name='JetStar')
        airline_spiceair = PublicsAirlineCompanyFactory(name='SpiceAir')

        # First travel setup
        travel_1 = TravelFactory(
            traveler=self.traveler, supervisor=self.unicef_staff)
        travel_1.itinerary.all().delete()

        itinerary_item_1 = ItineraryItemFactory(travel=travel_1,
                                                origin='Origin1',
                                                destination='Origin2',
                                                departure_date=datetime.datetime(
                                                    2016, 12, 3, 11, tzinfo=UTC),
                                                arrival_date=datetime.datetime(
                                                    2016, 12, 3, 12, tzinfo=UTC),
                                                mode_of_travel=ModeOfTravel.CAR,
                                                dsa_region=dsa_brd)
        itinerary_item_1.airlines.all().delete()

        itinerary_item_2 = ItineraryItemFactory(travel=travel_1,
                                                origin='Origin2',
                                                destination='Origin3',
                                                departure_date=datetime.datetime(
                                                    2016, 12, 5, 11, tzinfo=UTC),
                                                arrival_date=datetime.datetime(
                                                    2016, 12, 5, 12, tzinfo=UTC),
                                                mode_of_travel=ModeOfTravel.PLANE,
                                                dsa_region=dsa_lan)
        itinerary_item_2.airlines.all().delete()
        itinerary_item_2.airlines.add(airline_jetstar)

        itinerary_item_3 = ItineraryItemFactory(travel=travel_1,
                                                origin='Origin3',
                                                destination='Origin1',
                                                departure_date=datetime.datetime(
                                                    2016, 12, 6, 11, tzinfo=UTC),
                                                arrival_date=datetime.datetime(
                                                    2016, 12, 6, 12, tzinfo=UTC),
                                                mode_of_travel=ModeOfTravel.PLANE,
                                                dsa_region=None)
        itinerary_item_3.airlines.all().delete()
        itinerary_item_3.airlines.add(airline_spiceair)

        # Second travel setup
        another_traveler = UserFactory(
            first_name='Max', last_name='Mustermann')
        travel_2 = TravelFactory(
            traveler=another_traveler, supervisor=self.unicef_staff)
        travel_2.itinerary.all().delete()

        itinerary_item_4 = ItineraryItemFactory(travel=travel_2,
                                                origin='Origin2',
                                                destination='Origin1',
                                                departure_date=datetime.datetime(
                                                    2016, 12, 5, 11, tzinfo=UTC),
                                                arrival_date=datetime.datetime(
                                                    2016, 12, 5, 12, tzinfo=UTC),
                                                mode_of_travel=ModeOfTravel.PLANE,
                                                dsa_region=dsa_lan)
        itinerary_item_4.airlines.all().delete()
        itinerary_item_4.airlines.add(airline_jetstar)

        itinerary_item_5 = ItineraryItemFactory(travel=travel_2,
                                                origin='Origin3',
                                                destination='Origin1',
                                                departure_date=datetime.datetime(
                                                    2016, 12, 6, 11, tzinfo=UTC),
                                                arrival_date=datetime.datetime(
                                                    2016, 12, 6, 12, tzinfo=UTC),
                                                mode_of_travel=ModeOfTravel.CAR,
                                                dsa_region=None)
        itinerary_item_5.airlines.all().delete()
        itinerary_item_5.airlines.add(airline_spiceair)

        with self.assertNumQueries(6):
            response = self.forced_auth_req('get', reverse('t2f:travels:list:travel_admin_export'),
                                            user=self.unicef_staff)
        export_csv = csv.reader(StringIO(response.content.decode('utf-8')))
        rows = [r for r in export_csv]

        self.assertEqual(len(rows), 6)

        # check header
        self.assertEqual(rows[0],
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

        self.assertEqual(rows[1],
                         ['{}/1'.format(datetime.datetime.now().year),
                          'John Doe',
                          travel_1.office.name,
                          travel_1.section.name,
                          'planned',
                          'Origin1',
                          'Origin2',
                          '03-Dec-2016',
                          '03-Dec-2016',
                          'BRD',
                          '',
                          'Car',
                          ''])

        self.assertEqual(rows[2],
                         ['{}/1'.format(datetime.datetime.now().year),
                          'John Doe',
                          travel_1.office.name,
                          travel_1.section.name,
                          'planned',
                          'Origin2',
                          'Origin3',
                          '05-Dec-2016',
                          '05-Dec-2016',
                          'LAN',
                          '',
                          'Plane',
                          'JetStar'])

        self.assertEqual(rows[3],
                         ['{}/1'.format(datetime.datetime.now().year),
                          'John Doe',
                          travel_1.office.name,
                          travel_1.section.name,
                          'planned',
                          'Origin3',
                          'Origin1',
                          '06-Dec-2016',
                          '06-Dec-2016',
                          'NODSA',
                          '',
                          'Plane',
                          'SpiceAir'])

        self.assertEqual(rows[4],
                         ['{}/2'.format(datetime.datetime.now().year),
                          'Max Mustermann',
                          travel_2.office.name,
                          travel_2.section.name,
                          'planned',
                          'Origin2',
                          'Origin1',
                          '05-Dec-2016',
                          '05-Dec-2016',
                          'LAN',
                          '',
                          'Plane',
                          'JetStar'])

        self.assertEqual(rows[5],
                         ['{}/2'.format(datetime.datetime.now().year),
                          'Max Mustermann',
                          travel_2.office.name,
                          travel_2.section.name,
                          'planned',
                          'Origin3',
                          'Origin1',
                          '06-Dec-2016',
                          '06-Dec-2016',
                          'NODSA',
                          '',
                          'Car',
                          'SpiceAir'])
