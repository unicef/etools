from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.transaction import atomic

from et2f import PULI_USER_USERNAME, PULI_USER_PASSWORD
from et2f.models import Currency
from users.models import Country


class Command(BaseCommand):
    @atomic
    def handle(self, *args, **options):
        user = self._create_admin_user()
        connection.set_tenant(user.profile.country)

        self._load_currencies()
        self._load_users()

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

    def _load_travel_types(self):
        # "Plane", "Boat", "Car", "Train"
        pass

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

# a = {
#     "partner": [
#         {
#             "value": 0,
#             "label": "Dynazzy"
#         },
#         {
#             "value": 1,
#             "label": "Yodoo"
#         },
#         {
#             "value": 2,
#             "label": "Omba"
#         },
#         {
#             "value": 3,
#             "label": "Eazzy"
#         },
#         {
#             "value": 4,
#             "label": "Avamba"
#         },
#         {
#             "value": 5,
#             "label": "Jaxworks"
#         },
#         {
#             "value": 6,
#             "label": "Thoughtmix"
#         },
#         {
#             "value": 7,
#             "label": "Bubbletube"
#         },
#         {
#             "value": 8,
#             "label": "Mydo"
#         },
#         {
#             "value": 9,
#             "label": "Photolist"
#         },
#         {
#             "value": 10,
#             "label": "Gevee"
#         },
#         {
#             "value": 11,
#             "label": "Buzzdog"
#         },
#         {
#             "value": 12,
#             "label": "Quinu"
#         },
#         {
#             "value": 13,
#             "label": "Edgewire"
#         },
#         {
#             "value": 14,
#             "label": "Yambee"
#         },
#         {
#             "value": 15,
#             "label": "Ntag"
#         },
#         {
#             "value": 16,
#             "label": "Muxo"
#         },
#         {
#             "value": 17,
#             "label": "Edgetag"
#         },
#         {
#             "value": 18,
#             "label": "Tagfeed"
#         },
#         {
#             "value": 19,
#             "label": "BlogXS"
#         },
#         {
#             "value": 20,
#             "label": "Feedbug"
#         },
#         {
#             "value": 21,
#             "label": "Babblestorm"
#         },
#         {
#             "value": 22,
#             "label": "Skimia"
#         },
#         {
#             "value": 23,
#             "label": "Linkbridge"
#         },
#         {
#             "value": 24,
#             "label": "Fatz"
#         },
#         {
#             "value": 25,
#             "label": "Kwimbee"
#         },
#         {
#             "value": 26,
#             "label": "Yodo"
#         },
#         {
#             "value": 27,
#             "label": "Skibox"
#         },
#         {
#             "value": 28,
#             "label": "Zoomzone"
#         },
#         {
#             "value": 29,
#             "label": "Meemm"
#         },
#         {
#             "value": 30,
#             "label": "Twitterlist"
#         },
#         {
#             "value": 31,
#             "label": "Kwilith"
#         },
#         {
#             "value": 32,
#             "label": "Skipfire"
#         },
#         {
#             "value": 33,
#             "label": "Wikivu"
#         },
#         {
#             "value": 34,
#             "label": "Topicblab"
#         },
#         {
#             "value": 35,
#             "label": "BlogXS"
#         },
#         {
#             "value": 36,
#             "label": "Brightbean"
#         },
#         {
#             "value": 37,
#             "label": "Skimia"
#         },
#         {
#             "value": 38,
#             "label": "Mycat"
#         },
#         {
#             "value": 39,
#             "label": "Tagcat"
#         },
#         {
#             "value": 40,
#             "label": "Meedoo"
#         },
#         {
#             "value": 41,
#             "label": "Vitz"
#         },
#         {
#             "value": 42,
#             "label": "Realblab"
#         },
#         {
#             "value": 43,
#             "label": "Babbleopia"
#         },
#         {
#             "value": 44,
#             "label": "Pixonyx"
#         },
#         {
#             "value": 45,
#             "label": "Dabshots"
#         },
#         {
#             "value": 46,
#             "label": "Gabcube"
#         },
#         {
#             "value": 47,
#             "label": "Yoveo"
#         },
#         {
#             "value": 48,
#             "label": "Realblab"
#         },
#         {
#             "value": 49,
#             "label": "Tagcat"
#         }
#     ],
# 
# }
