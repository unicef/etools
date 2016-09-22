import os
from django.core.management.base import BaseCommand, CommandError
from users.models import UserProfile, Country, Office, Section
from django.contrib.auth.models import User, Group

USERNAME = os.environ.get('TEST_USERNAME')
PASSWORD = os.environ.get('TEST_PASSWORD')

class Command(BaseCommand):
    help = 'Creates new test users'

    def add_arguments(self, parser):
        parser.add_argument('num_users', type=int, help='Number of test users to create')

    def handle(self, *args, **options):
        try:
            num_Test_Users = User.objects.filter(username__startswith = USERNAME).count()
            num_New_Users = options['num_users']
            g = Group.objects.get(name='UNICEF User')
            country = Country.objects.get(name='UAT')
            for i in xrange(num_Test_Users, num_Test_Users + num_New_Users):
                user = User.objects.create_user(username=USERNAME + str(i),
                                                email=USERNAME + str(i) + "@unicef.org",
                                                password=PASSWORD)
                user.is_staff = True
                user.groups.add(g)
                user.save()
                userp = UserProfile.objects.get(user=user)
                userp.country = country
                userp.countries_available.add(country)
                userp.country_override = country

                userp.save()

            if num_New_Users > 0:
                self.stdout.write('Successfully created ' + str(num_New_Users) + ' new users')
            else:
                self.stdout.write('Please enter an integer greater than 0')
        except Exception as exp:
            raise CommandError(exp.message)