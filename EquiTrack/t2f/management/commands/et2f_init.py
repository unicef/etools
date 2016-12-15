# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.transaction import atomic

from t2f.models import Currency, AirlineCompany, DSARegion, ExpenseType, WBS, Grant, Fund, TravelType, ModeOfTravel
from partners.models import PartnerOrganization
from users.models import Country, Office

from _private import populate_permission_matrix


# DEVELOPMENT CODE -
class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('username', nargs=1)
        parser.add_argument('password', nargs=1, default='password')
        parser.add_argument('-u', '--with_users', action='store_true', default=False)
        parser.add_argument('-o', '--with_offices', action='store_true', default=False)
        parser.add_argument('-p', '--with_partners', action='store_true', default=False)

    @atomic
    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        user = self._get_or_create_admin_user(username, password)
        connection.set_tenant(user.profile.country)

        self._load_travel_types()
        self._load_travel_modes()
        self._load_currencies()

        if options.get('with_users'):
            self._load_users()

        self._load_airlines()

        if options.get('with_offices'):
            self._load_offices()

        if options.get('with_partners'):
            self._load_partners()

        self._load_dsa_regions()
        self._load_permission_matrix()
        self._add_wbs()
        self._add_grants()
        self._add_funds()
        self._add_expense_types()
        self._add_user_groups()

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

    def _load_travel_types(self):
        for travel_type in TravelType.CHOICES:
            tt, created = TravelType.objects.get_or_create(name=travel_type[0])
            if created:
                self.stdout.write('Travel type created: {}'.format(travel_type[0]))
            else:
                self.stdout.write('Travel type found: {}'.format(travel_type[0]))

    def _load_travel_modes(self):
        for travel_mode in ModeOfTravel.CHOICES:
            mot, created = ModeOfTravel.objects.get_or_create(name=travel_mode[0])
            if created:
                self.stdout.write('Travel mode created: {}'.format(travel_mode[0]))
            else:
                self.stdout.write('Travel mode found: {}'.format(travel_mode[0]))

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
        airlines = [('American Airlines', 'AA', 1, 'AAL', 'United States'),
                    ('Blue Panorama', 'BV', 4, 'BPA', 'Italy'),
                    ('Adria Airways', 'JP', 165, 'ADR', 'Slovenia'),
                    ('Aegean Airlines', 'A3', 390, 'AEE', 'Greece'),
                    ('Aerolineas Argentinas', 'AR', 44, 'ARG', 'Argentina'),
                    ('Aeromexico', 'AM', 139, 'AMX', 'Mexico'),
                    ('Air Algérie', 'AH', 124, 'DAH', 'Algeria'),
                    ('Air Berlin', 'AB', 745, 'BER', 'Germany'),
                    ('Air Burkina', '2J', 226, 'VBW', 'Burkina Faso'),
                    ('Air Caledonie', 'TY', 190, 'TPC', 'New Caledonia'),
                    ('Air Canada', 'AC', 14, 'ACA', 'Canada'),
                    ('Air Europa', 'UX', 996, 'AEA', 'Spain'),
                    ('Air France', 'AF', 57, 'AFR', 'France'),
                    ('Air India ', 'AI', 98, 'AIC', 'India'),
                    ('Air Koryo', 'JS', 120, 'KOR', 'Korea, Democratic People\'s Republic of'),
                    ('Air Madagascar', 'MD', 258, 'MDG', 'Madagascar'),
                    ('Air Mauritius', 'MK', 239, 'MAU', 'Mauritius'),
                    ('Air SERBIA a.d. Beograd', 'JU', 115, 'ASL', 'Serbia'),
                    ('Air Seychelles', 'HM', 61, 'SEY', 'Seychelles'),
                    ('Aircalin', 'SB', 63, 'ACI', 'New Caledonia'),
                    ('Alaska Airlines', 'AS', 27, 'ASA', 'United States'),
                    ('Alitalia', 'AZ', 55, 'AZA', 'Italy'),
                    ('All Nippon Airways', 'NH', 205, 'ANA', 'Japan'),
                    ('AlMasria Universal Airlines', 'UJ', 110, 'LMU', 'Egypt'),
                    ('Arik Air', 'W3', 725, 'ARA', 'Nigeria'),
                    ('Arkia Israeli Airlines ', 'IZ', 238, 'AIZ', 'Israel'),
                    ('Asiana', 'OZ', 988, 'AAR', 'Korea'),
                    ('AVIANCA', 'AV', 134, 'AVA', 'Colombia'),
                    ('Azul Brazilian Airlines', 'AD', 577, 'AZU', 'Brazil'),
                    ('Bangkok Air ', 'PG', 829, 'BKP', 'Thailand'),
                    ('British Airways', 'BA', 125, 'BAW', 'United Kingdom'),
                    ('Brussels Airlines', 'SN', 82, 'BEL', 'Belgium'),
                    ('Camair-Co', 'QC', 40, '0', 'Cameroon'),
                    ('Cargolux S.A.', 'CV', 172, 'CLX', 'Luxembourg'),
                    ('Caribbean Airlines', 'BW', 106, 'BWA', 'Trinidad and Tobago'),
                    ('Carpatair', 'V3', 21, 'KRP', 'Romania'),
                    ('Cathay Dragon', 'KA', 43, 'HDA', 'Hong Kong SAR, China'),
                    ('Cathay Pacific', 'CX', 160, 'CPA', 'Hong Kong SAR, China'),
                    ('China Eastern', 'MU', 781, 'CES', 'China (People\'s Republic of)'),
                    ('China Southern Airlines', 'CZ', 784, 'CSN', 'China (People\'s Republic of)'),
                    ('Comair', 'MN', 161, 'CAW', 'South Africa'),
                    ('Czech Airlines j.s.c', 'OK', 64, 'CSA', 'Czech Republic'),
                    ('Delta Air Lines', 'DL', 6, 'DAL', 'United States'),
                    ('DHL Aviation EEMEA B.S.C.(c) ', 'ES*', 155, 'DHX', 'Bahrain'),
                    ('Dniproavia', 'Z6*', 181, 'UDN', 'Ukraine'),
                    ('Egyptair', 'MS', 77, 'MSR', 'Egypt'),
                    ('EL AL', 'LY', 114, 'ELY', 'Israel'),
                    ('Emirates', 'EK', 176, 'UAE', 'United Arab Emirates'),
                    ('Ethiopian Airlines', 'ET', 71, 'ETH', 'Ethiopia'),
                    ('Etihad Airways', 'EY', 607, 'ETD', 'United Arab Emirates'),
                    ('Eurowings', 'EW', 104, 'EWG', 'Germany'),
                    ('Fiji Airways', 'FJ', 260, 'FJI', 'Fiji'),
                    ('Finnair', 'AY', 105, 'FIN', 'Finland'),
                    ('flybe', 'BE', 267, 'BEE', 'United Kingdom'),
                    ('flydubai', 'FZ', 141, 'FDB', 'United Arab Emirates'),
                    ('Garuda', 'GA', 126, 'GIA', 'Indonesia'),
                    ('Germania', 'ST', 246, 'GMI', 'Germany'),
                    ('Hahn Air', 'HR*', 169, 'HHN', 'Germany'),
                    ('Hawaiian Airlines', 'HA', 173, 'HAL', 'United States'),
                    ('IBERIA', 'IB', 75, 'IBE', 'Spain'),
                    ('Icelandair', 'FI', 108, 'ICE', 'Iceland'),
                    ('Iran Air', 'IR', 96, 'IRA', 'Iran, Islamic Republic of'),
                    ('Japan Airlines', 'JL', 131, 'JAL', 'Japan'),
                    ('Jet Airways', '9W', 589, 'JAI', 'India'),
                    ('JetBlue', 'B6', 279, 'JBU', 'United States'),
                    ('Kenya Airways', 'KQ', 706, 'KQA', 'Kenya'),
                    ('KLM', 'KL', 74, 'KLM', 'Netherlands'),
                    ('Korean Air', 'KE', 180, 'KAL', 'Korea'),
                    ('Kuwait Airways', 'KU', 229, 'KAC', 'Kuwait'),
                    ('LACSA', 'LR', 133, 'LRC', 'Costa Rica'),
                    ('LAM', 'TM', 68, 'LAM', 'Mozambique'),
                    ('Lao Airlines', 'QV', 627, 'LAO', 'Lao People\'s Democratic Republic'),
                    ('LATAM Airlines Brasil', 'JJ', 957, 'TAM', 'Brazil'),
                    ('LATAM Airlines Colombia', '4C', 35, 'ARE', 'Colombia'),
                    ('LATAM Airlines Group', 'LA', 45, 'LAN', 'Chile'),
                    ('LATAM Cargo Chile', 'UC', 145, 'LCO', 'Chile'),
                    ('LOT Polish Airlines', 'LO', 80, 'LOT', 'Poland'),
                    ('Lufthansa', 'LH', 220, 'DLH', 'Germany'),
                    ('Malaysia Airlines', 'MH', 232, 'MAS', 'Malaysia'),
                    ('MEA', 'ME', 76, 'MEA', 'Lebanon'),
                    ('Olympic Air', 'OA', 50, 'OAL', 'Greece'),
                    ('Oman Air', 'WY', 910, 'OAS', 'Oman'),
                    ('Pegasus Airlines', 'PC', 624, 'PGT', 'Turkey'),
                    ('Philippine Airlines', 'PR', 79, 'PAL', 'Philippines'),
                    ('PIA', 'PK', 214, 'PIA', 'Pakistan'),
                    ('Qatar Airways', 'QR', 157, 'QTR', 'Qatar'),
                    ('Rossiya Airlines ', 'FV', 195, 'SDM', 'Russian Federation'),
                    ('Royal Air Maroc', 'AT', 147, 'RAM', 'Morocco'),
                    ('Royal Jordanian', 'RJ', 512, 'RJA', 'Jordan'),
                    ('SAA', 'SA', 83, 'SAA', 'South Africa'),
                    ('SAS', 'SK', 117, 'SAS', 'Sweden'),
                    ('Saudi Arabian Airlines', 'SV', 65, 'SVA', 'Saudi Arabia'),
                    ('Shanghai Airlines', 'FM', 774, '0', 'China (People\'s Republic of)'),
                    ('Sichuan Airlines ', '3U', 876, '0', 'China (People\'s Republic of)'),
                    ('SriLankan', 'UL', 603, 'ALK', 'Sri Lanka'),
                    ('SWISS', 'LX', 724, 'SWR', 'Switzerland'),
                    ('Syrianair', 'RB', 70, 'SYR', 'Syrian Arab Republic'),
                    ('TAME - Linea Aérea del Ecuador', 'EQ', 269, 'TAE', 'Ecuador'),
                    ('TAP Portugal', 'TP', 47, 'TAP', 'Portugal'),
                    ('TAROM ', 'RO', 281, 'ROT', 'Romania'),
                    ('Thai Airways International', 'TG', 217, 'THA', 'Thailand'),
                    ('THY - Turkish Airlines', 'TK', 235, 'THY', 'Turkey'),
                    ('Ukraine International Airlines', 'PS', 566, 'AUI', 'Ukraine'),
                    ('United Airlines', 'UA', 16, 'UAL', 'United States'),
                    ('UTair', 'UT', 298, 'UTA', 'Russian Federation'),
                    ('Uzbekistan Airways', 'HY', 250, 'UZB', 'Uzbekistan'),
                    ('Vietnam Airlines', 'VN', 738, 'HVN', 'Vietnam'),
                    ('Virgin Atlantic', 'VS', 932, 'VIR', 'United Kingdom'),
                    ('Virgin Australia', 'VA', 795, 'VAU', 'Australia'),
                    ('VRG Linhas Aéreas S.A. - Grupo GOL', 'G3', 127, 'GLO', 'Brazil'),
                    ('WestJet', 'WS', 838, 'WJA', 'Canada'),
                    ('White coloured by you', 'WI', 97, 'WHT', 'Portugal')]

        AirlineCompany.objects.all().delete()

        for airline_name, iata, code, icao, country in airlines:
            a, created = AirlineCompany.objects.get_or_create(name=airline_name, defaults={'iata': iata,
                                                                                           'code': code,
                                                                                           'icao': icao,
                                                                                           'country': country})
            if created:
                self.stdout.write('Airline created: {}'.format(airline_name))
            else:
                self.stdout.write('Airline found: {}'.format(airline_name))

    def _load_offices(self):
        offices = ('Pulilab', 'Unicef HQ')

        for office_name in offices:
            o, created = Office.objects.get_or_create(name=office_name)
            if created:
                o.offices.add(connection.tenant)
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
        wbs_data_list = [
            {'name': 'WBS #1'},
            {'name': 'WBS #2'},
            {'name': 'WBS #3'},
        ]

        for data in wbs_data_list:
            name = data.pop('name')
            r, created = WBS.objects.get_or_create(name=name)
            if created:
                self.stdout.write('WBS created: {}'.format(name))
            else:
                self.stdout.write('WBS found: {}'.format(name))

    def _add_grants(self):
        wbs_1 = WBS.objects.get(name='WBS #1')
        wbs_2 = WBS.objects.get(name='WBS #2')
        wbs_3 = WBS.objects.get(name='WBS #3')

        grant_data_list = [
            {'name': 'Grant #1',
             'wbs': wbs_1},
            {'name': 'Grant #2',
             'wbs': wbs_1},
            {'name': 'Grant #3',
             'wbs': wbs_2},
            {'name': 'Grant #4',
             'wbs': wbs_2},
            {'name': 'Grant #5',
             'wbs': wbs_3}
        ]

        for data in grant_data_list:
            name = data.pop('name')
            g, created = Grant.objects.get_or_create(name=name, defaults=data)
            if created:
                self.stdout.write('Grant created: {}'.format(name))
            else:
                self.stdout.write('Grant found: {}'.format(name))

    def _add_funds(self):
        grant_1 = Grant.objects.get(name='Grant #1')
        grant_2 = Grant.objects.get(name='Grant #2')
        grant_3 = Grant.objects.get(name='Grant #3')
        grant_4 = Grant.objects.get(name='Grant #4')
        grant_5 = Grant.objects.get(name='Grant #5')

        fund_data_list = [
            {'name': 'Fund #1',
             'grant': grant_1},
            {'name': 'Fund #2',
             'grant': grant_1},
            {'name': 'Fund #3',
             'grant': grant_2},
            {'name': 'Fund #4',
             'grant': grant_3},
            {'name': 'Fund #5',
             'grant': grant_3},
            {'name': 'Fund #6',
             'grant': grant_4},
            {'name': 'Fund #7',
             'grant': grant_4},
            {'name': 'Fund #8',
             'grant': grant_5},
            {'name': 'Fund #4',
             'grant': grant_5},
            {'name': 'Fund #4',
             'grant': grant_5},
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

    def _add_user_groups(self):
        group_names = ['Representative Office',
                       'Finance Focal Point',
                       'Travel Focal Point',
                       'Travel Administrator']
        for name in group_names:
            g, created = Group.objects.get_or_create(name=name)
            if created:
                self.stdout.write('Group created: {}'.format(name))
            else:
                self.stdout.write('Group found: {}'.format(name))

# DEVELOPMENT CODE - END
