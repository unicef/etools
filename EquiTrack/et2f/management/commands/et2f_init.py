from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.transaction import atomic

from et2f.models import Currency, AirlineCompany, DSARegion, Fund, ExpenseType
from funds.models import Donor, Grant
from partners.models import PartnerOrganization
from reports.models import Result, ResultType
from users.models import Country, Office

from _private import populate_permission_matrix


# DEVELOPMENT CODE -
class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('username', nargs=1)
        parser.add_argument('password', nargs=1, default='password')

    @atomic
    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        user = self._get_or_create_admin_user(username, password)
        connection.set_tenant(user.profile.country)

        self._load_currencies()
        self._load_users()
        self._load_airlines()
        self._load_offices()
        self._load_partners()
        self._load_dsa_regions()
        self._load_permission_matrix()
        self._add_wbs()

    def _get_or_create_admin_user(self, username, password):
        User = get_user_model()

        try:
            return User.objects.get(username=username)
        except ObjectDoesNotExist:
            pass

        uat_country = Country.objects.get(name='UAT')

        user = User(username=username,
                    first_name='Puli',
                    last_name='Lab',
                    is_superuser=True,
                    is_staff=True)
        user.set_password(password)
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
        populate_permission_matrix(self)

    def _add_wbs(self):
        Result.objects.all().delete()

        result_type = ResultType.objects.get(name=ResultType.ACTIVITY)

        wbs_data_list = [
            {'name': 'WBS #1',
             'wbs': 'wbs_1',
             'result_type': result_type},
            {'name': 'WBS #2',
             'wbs': 'wbs_2',
             'result_type': result_type},
            {'name': 'WBS #3',
             'wbs': 'wbs_3',
             'result_type': result_type},
        ]

        for data in wbs_data_list:
            wbs = data.pop('wbs')
            r, created = Result.objects.get_or_create(wbs=wbs, defaults=data)
            if created:
                self.stdout.write('WBS created: {}'.format(data['name']))
            else:
                self.stdout.write('WBS found: {}'.format(data['name']))

    def _add_grants(self):
        donor, c = Donor.objects.get_or_create(name='Donor')

        grant_data_list = [
            {'name': 'Grant #1',
             'donor': donor},
            {'name': 'Grant #2',
             'donor': donor},
            {'name': 'Grant #3',
             'donor': donor},
            {'name': 'Grant #4',
             'donor': donor},
            {'name': 'Grant #5',
             'donor': donor}
        ]

        for data in grant_data_list:
            name = data.pop('name')
            g, created = Grant.objects.get_or_create(name=name, defaults=data)
            if created:
                self.stdout.write('Grant created: {}'.format(name))
            else:
                self.stdout.write('Grant found: {}'.format(name))

    def _add_funds(self):
        fund_data_list = [
            {'name': 'Fund #1'},
            {'name': 'Fund #2'},
            {'name': 'Fund #3'},
            {'name': 'Fund #4'},
        ]

        for data in fund_data_list:
            name = data.pop('name')
            f, created = Fund.objects.get_or_create(name=name, defaults=data)
            if created:
                self.stdout.write('Fund created: {}'.format(name))
            else:
                self.stdout.write('Fund found: {}'.format(name))

    def _add_expense_types(self):
        expense_type_data = [
            {'title': 'Food',
             'code': 'food'},
            {'title': 'Tickets',
             'code': 'tickets'},
            {'title': 'Fees',
             'code': 'fees'}
        ]

        for data in expense_type_data:
            title = data.pop('title')
            e, created = ExpenseType.objects.get_or_create(title=title, defaults=data)
            if created:
                self.stdout.write('Expense type created: {}'.format(title))
            else:
                self.stdout.write('Expense type found: {}'.format(title))

# DEVELOPMENT CODE - END