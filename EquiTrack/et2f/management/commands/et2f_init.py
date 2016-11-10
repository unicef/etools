from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.transaction import atomic

from et2f import PULI_USER_USERNAME, PULI_USER_PASSWORD, UserTypes, TripStatus
from et2f.models import Currency, AirlineCompany, DSARegion, TravelPermission
from partners.models import PartnerOrganization
from users.models import Country, Office

# DEVELOPMENT CODE -
class Command(BaseCommand):
    @atomic
    def handle(self, *args, **options):
        user = self._create_admin_user()
        connection.set_tenant(user.profile.country)

        self._load_currencies()
        self._load_users()
        self._load_airlines()
        self._load_offices()
        self._load_partners()
        self._load_dsa_regions()
        self._load_permission_matrix()

    def _create_admin_user(self):
        User = get_user_model()

        try:
            return User.objects.get(username=PULI_USER_USERNAME)
        except ObjectDoesNotExist:
            pass

        uat_country = Country.objects.get(name='UAT')

        user = User(username=PULI_USER_USERNAME,
                    first_name='Puli',
                    last_name='Lab',
                    is_superuser=True,
                    is_staff=True)
        user.set_password(PULI_USER_PASSWORD)
        user.save()

        profile = user.profile
        profile.country = profile.country_override = uat_country
        profile.save()

        self.stdout.write('User was successfully created.')
        return user

    def _load_currencies(self):
        data = [('United States dollar', 'USD'),
                ('Euro', 'EUR'),
                ('Japanese yen', 'JPY'),
                ('Pound sterling', 'GBP'),
                ('Australian dollar', 'AUD'),
                ('Canadian dollar', 'CAD'),
                ('Swiss franc', 'CHF'),
                ('Chinese yuan', 'CNY'),
                ('Swedish krona', 'SEK'),
                ('Mexican peso', 'MXN'),
                ('New Zealand dollar', 'NZD'),
                ('Singapore dollar', 'SGD'),
                ('Hong Kong dollar', 'HKD'),
                ('Norwegian krone', 'NOK'),
                ('South Korean won', 'KRW'),
                ('Turkish lira', 'TRY'),
                ('Indian rupee', 'INR'),
                ('Russian ruble', 'RUB'),
                ('Brazilian real', 'BRL'),
                ('South African rand', 'ZAR')]

        for name, iso_4217 in data:
            c, created = Currency.objects.get_or_create(name=name, iso_4217=iso_4217)
            if created:
                self.stdout.write('Currency created: {} ({})'.format(name, iso_4217))
            else:
                self.stdout.write('Currency found: {} ({})'.format(name, iso_4217))

    def _load_users(self):
        User = get_user_model()
        user_full_names = ['Kathryn Cruz', 'Jonathan Wright', 'Timothy Kelly', 'Brenda Nguyen', 'Matthew Morales',
                           'Timothy Watson', 'Jacqueline Brooks', 'Steve Olson', 'Lawrence Patterson', 'Lois Jones',
                           'Margaret White', 'Clarence Stanley', 'Bruce Williamson', 'Susan Carroll', 'Philip Wood',
                           'Emily Jenkins', 'Christina Robinson', 'Jason Young', 'Joyce Freeman', 'Jack Murphy',
                           'Katherine Garcia', 'Sean Perkins', 'Howard Peterson', 'Denise Coleman', 'Benjamin Evans',
                           'Carl Watkins', 'Martin Morris', 'Nicole Stephens', 'Thomas Willis', 'Ann Ferguson',
                           'Russell Hanson', 'Janet Johnston', 'Adam Bowman', 'Elizabeth Mendoza', 'Helen Robertson',
                           'Wanda Fowler', 'Roger Richardson', 'Bobby Carroll', 'Donna Sims', 'Shawn Peters',
                           'Lisa Davis', 'Laura Riley', 'Jason Freeman', 'Ashley Hill', 'Joseph Gonzales',
                           'Brenda Dixon', 'Paul Wilson', 'Tammy Reyes', 'Beverly Bishop', 'James Weaver',
                           'Samuel Vasquez', 'Albert Baker', 'Keith Wright', 'Michael Hart', 'Shirley Allen',
                           'Samuel Gutierrez', 'Cynthia Riley', 'Roy Simpson', 'Raymond Wagner', 'Eric Taylor',
                           'Steven Bell', 'Jane Powell', 'Paula Morales', 'James Hamilton', 'Shirley Perez',
                           'Maria Olson', 'Amy Dunn', 'Frances Bowman', 'Billy Lawrence', 'Beverly Howell', 'Amy Sims',
                           'Carlos Sanchez', 'Nicholas Harvey', 'Walter Wheeler', 'Bruce Morales', 'Kathy Reynolds',
                           'Lisa Lopez', 'Ann Medina', 'Raymond Washington', 'Jessica Brown', 'Harold Stone',
                           'Paul Hill', 'Wayne Foster', 'Brian Garza', 'Craig Sims', 'Adam Morales', 'Brandon Miller',
                           'Dennis Green', 'Linda Banks', 'Sandra Dunn', 'Randy Rogers', 'Jimmy West', 'Julia Grant',
                           'Judy Ryan', 'William Carroll', 'Mary Rose', 'Ann Nelson', 'Rebecca Hill', 'Robert Rivera',
                           'Rebecca Weaver']

        for full_name in user_full_names:
            first_name, last_name = full_name.split()
            username = full_name.replace(' ', '_').lower()
            u, created = User.objects.get_or_create(username=username, defaults={'first_name': first_name,
                                                                                 'last_name': last_name})
            if created:
                self.stdout.write('User created: {} ({})'.format(full_name, username))
            else:
                self.stdout.write('User found: {} ({})'.format(full_name, username))

    def _load_airlines(self):
        airlines = ('Emirates', 'Qatar Airways', 'Singapore Airlines', 'Cathay Pacific', 'ANAs', 'Etihad Airways',
                    'Turkish Airlines', 'EVA Air', 'Qantas Airways', 'Lufthansa', 'Garuda Indonesia', 'Hainan Airlines',
                    'Thai Airways', 'Air France', 'Swiss Int\'l Air Lines', 'Asiana Airlines ', 'Air New Zealand',
                    'Virgin Australia', 'Austrian', 'Bangkok Airways', 'Japan Airlines', 'Dragonair', 'AirAsia', 'KLM',
                    'Virgin America', 'British Airways', 'Finnair', 'Virgin Atlantic', 'Hong Kong Airlines',
                    'Norwegian', 'Air Canada', 'China Southern', 'Aegean Airlines', 'Malaysia Airlines',
                    'Delta Air Lines', 'Korean Air', 'China Airlines', 'easyJet', 'SilkAir', 'Aeroflot',
                    'South African Airways', 'Oman Air', 'Air Astana', 'Vietnam Airlines', 'LAN Airlines',
                    'Jetstar Airways', 'Porter Airlines', 'AirAsiaX', 'Aer Lingus', 'WestJet', 'Indigo', 'Iberia',
                    'jetBlue Airways', 'Jetstar Asia', 'Azul Airlines', 'Avianca', 'TAM Airlines', 'Alitalia',
                    'Brussels Airlines', 'Alaska Airlines', 'Scoot', 'SAS Scandinavian', 'Air Seychelles',
                    'TAP Air Portugal', 'Thomson Airways', 'Southwest Airlines', 'SriLankan Airlines',
                    'United Airlines', 'Copa Airlines', 'Azerbaijan Airlines', 'Jet Airways', 'Hawaiian Airlines ',
                    'Air Mauritius', 'Air Berlin', 'Eurowings', 'Ethiopian Airlines', 'American Airlines', 'Peach',
                    'China Eastern', 'Gulf Air', 'Icelandair', 'Saudi Arabian Airlines', 'Philippine Airlines',
                    'American Eagle ', 'Kenya Airways', 'TAAG Angola ', 'Air China', 'Air Transat', 'Air Nostrum',
                    'Juneyao Airlines', 'Fiji Airways', 'LOT Polish', 'Kulula', 'Aeromexico', 'Royal Brunei Airlines',
                    'Tianjin Airlines', 'Tiger Airways ', 'Mango ', 'Royal Jordanian', 'SpiceJet ')

        for airline_name in airlines:
            a, created = AirlineCompany.objects.get_or_create(name=airline_name, defaults={'code': '-'})
            if created:
                self.stdout.write('Airline created: {}'.format(airline_name))
            else:
                self.stdout.write('Airline found: {}'.format(airline_name))

    def _load_offices(self):
        offices = ('Pulilab', 'Unicef HQ')

        for office_name in offices:
            o, created = Office.objects.get_or_create(name=office_name)
            if created:
                self.stdout.write('Office created: {}'.format(office_name))
            else:
                self.stdout.write('Office found: {}'.format(office_name))

    def _load_partners(self):
        partners = ['Dynazzy', 'Yodoo', 'Omba', 'Eazzy', 'Avamba', 'Jaxworks', 'Thoughtmix', 'Bubbletube', 'Mydo',
                    'Photolist', 'Gevee', 'Buzzdog', 'Quinu', 'Edgewire', 'Yambee', 'Ntag', 'Muxo',
                    'Edgetag', 'Tagfeed', 'BlogXS', 'Feedbug', 'Babblestorm', 'Skimia', 'Linkbridge', 'Fatz', 'Kwimbee',
                    'Yodo', 'Skibox', 'Zoomzone', 'Meemm', 'Twitterlist', 'Kwilith', 'Skipfire', 'Wikivu', 'Topicblab',
                    'BlogXS', 'Brightbean', 'Skimia', 'Mycat', 'Tagcat', 'Meedoo', 'Vitz', 'Realblab', 'Babbleopia',
                    'Pixonyx', 'Dabshots', 'Gabcube', 'Yoveo', 'Realblab', 'Tagcat']

        for partner_name in partners:
            p, created = PartnerOrganization.objects.get_or_create(name=partner_name)
            if created:
                self.stdout.write('Partner created: {}'.format(partner_name))
            else:
                self.stdout.write('Partner found: {}'.format(partner_name))


    def _load_dsa_regions(self):
        dsa_region_data = [{'dsa_amount_usd': 300,
                            'name': 'Hungary',
                            'room_rate': 120,
                            'dsa_amount_60plus_usd': 200,
                            'dsa_amount_60plus_local': 56000,
                            'dsa_amount_local': 84000},
                           {'dsa_amount_usd': 400,
                            'name': 'Germany',
                            'room_rate': 150,
                            'dsa_amount_60plus_usd': 260,
                            'dsa_amount_60plus_local': 238.68,
                            'dsa_amount_local': 367.21}]
        for data in dsa_region_data:
            name = data.pop('name')
            d, created = DSARegion.objects.get_or_create(name=name, defaults=data)
            if created:
                self.stdout.write('DSA Region created: {}'.format(name))
            else:
                self.stdout.write('DSA Region found: {}'.format(name))


    def _load_permission_matrix(self):
        perm_codes = ['can_see_iteneraryitem_id',
                      'can_edit_iteneraryitem_id',
                      'can_see_iteneraryitem_origin',
                      'can_edit_iteneraryitem_origin',
                      'can_see_iteneraryitem_destination',
                      'can_edit_iteneraryitem_destination',
                      'can_see_iteneraryitem_departure_date',
                      'can_edit_iteneraryitem_departure_date',
                      'can_see_iteneraryitem_arrival_date',
                      'can_edit_iteneraryitem_arrival_date',
                      'can_see_iteneraryitem_dsa_region',
                      'can_edit_iteneraryitem_dsa_region',
                      'can_see_iteneraryitem_overnight_travel',
                      'can_edit_iteneraryitem_overnight_travel',
                      'can_see_iteneraryitem_mode_of_travel',
                      'can_edit_iteneraryitem_mode_of_travel',
                      'can_see_iteneraryitem_airlines',
                      'can_edit_iteneraryitem_airlines',
                      'can_see_expense_id',
                      'can_edit_expense_id',
                      'can_see_expense_type',
                      'can_edit_expense_type',
                      'can_see_expense_document_currency',
                      'can_edit_expense_document_currency',
                      'can_see_expense_account_currency',
                      'can_edit_expense_account_currency',
                      'can_see_expense_amount',
                      'can_edit_expense_amount',
                      'can_see_deduction_id',
                      'can_edit_deduction_id',
                      'can_see_deduction_date',
                      'can_edit_deduction_date',
                      'can_see_deduction_breakfast',
                      'can_edit_deduction_breakfast',
                      'can_see_deduction_lunch',
                      'can_edit_deduction_lunch',
                      'can_see_deduction_dinner',
                      'can_edit_deduction_dinner',
                      'can_see_deduction_accomodation',
                      'can_edit_deduction_accomodation',
                      'can_see_deduction_no_dsa',
                      'can_edit_deduction_no_dsa',
                      'can_see_deduction_day_of_the_week',
                      'can_edit_deduction_day_of_the_week',
                      'can_see_costassignment_id',
                      'can_edit_costassignment_id',
                      'can_see_costassignment_wbs',
                      'can_edit_costassignment_wbs',
                      'can_see_costassignment_share',
                      'can_edit_costassignment_share',
                      'can_see_costassignment_grant',
                      'can_edit_costassignment_grant',
                      'can_see_clearances_id',
                      'can_edit_clearances_id',
                      'can_see_clearances_medical_clearance',
                      'can_edit_clearances_medical_clearance',
                      'can_see_clearances_security_clearance',
                      'can_edit_clearances_security_clearance',
                      'can_see_clearances_security_course',
                      'can_edit_clearances_security_course',
                      'can_see_travelactivity_id',
                      'can_edit_travelactivity_id',
                      'can_see_travelactivity_travel_type',
                      'can_edit_travelactivity_travel_type',
                      'can_see_travelactivity_partner',
                      'can_edit_travelactivity_partner',
                      'can_see_travelactivity_partnership',
                      'can_edit_travelactivity_partnership',
                      'can_see_travelactivity_result',
                      'can_edit_travelactivity_result',
                      'can_see_travelactivity_locations',
                      'can_edit_travelactivity_locations',
                      'can_see_travelactivity_primary_traveler',
                      'can_edit_travelactivity_primary_traveler',
                      'can_see_travelactivity_date',
                      'can_edit_travelactivity_date',
                      'can_see_travel_reference_number',
                      'can_edit_travel_reference_number',
                      'can_see_travel_supervisor',
                      'can_edit_travel_supervisor',
                      'can_see_travel_office',
                      'can_edit_travel_office',
                      'can_see_travel_end_date',
                      'can_edit_travel_end_date',
                      'can_see_travel_section',
                      'can_edit_travel_section',
                      'can_see_travel_international_travel',
                      'can_edit_travel_international_travel',
                      'can_see_travel_traveller',
                      'can_edit_travel_traveller',
                      'can_see_travel_start_date',
                      'can_edit_travel_start_date',
                      'can_see_travel_ta_required',
                      'can_edit_travel_ta_required',
                      'can_see_travel_purpose',
                      'can_edit_travel_purpose',
                      'can_see_travel_id',
                      'can_edit_travel_id',
                      'can_see_travel_itinerary',
                      'can_edit_travel_itinerary',
                      'can_see_travel_expenses',
                      'can_edit_travel_expenses',
                      'can_see_travel_deductions',
                      'can_edit_travel_deductions',
                      'can_see_travel_cost_assignments',
                      'can_edit_travel_cost_assignments',
                      'can_see_travel_clearances',
                      'can_edit_travel_clearances',
                      'can_see_travel_status',
                      'can_edit_travel_status',
                      'can_see_travel_activities',
                      'can_edit_travel_activities',
                      'can_see_travel_mode_of_travel',
                      'can_edit_travel_mode_of_travel',
                      'can_see_travel_estimated_travel_cost',
                      'can_edit_travel_estimated_travel_cost',
                      'can_see_travel_currency',
                      'can_edit_travel_currency']

        permissions = []
        for user_type in UserTypes.CHOICES:
            for status in TripStatus.CHOICES:
                for pc in perm_codes:

                    kwargs = dict(name='afd', code=pc, user_type=user_type[0], status=status[0], value=True)
                    permissions.append(TravelPermission(**kwargs))

        TravelPermission.objects.bulk_create(permissions)
# DEVELOPMENT CODE - END