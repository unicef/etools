import sys
from django.core.management.base import BaseCommand, CommandError
from users.models import UserProfile, Country, Office, Section
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Creates new test users with '             \
                'username: testuser_(num), '           \
                'email:    testuser_(num)@unicef.org, ' \
                'password: un1c3f, '                     \
                'country: uat'

    def add_arguments(self, parser):
        parser.add_argument('num_users', type=int, help='Number of test users to create')

    def handle(self, *args, **options):
        try:
            numTestUsers = User.objects.filter(username__startswith = 'testuser_').count()
            numNewUsers = options['num_users']
            for i in xrange(numTestUsers, numTestUsers + numNewUsers):
                user = User.objects.create_user(username="testuser_" + str(i),
                                                email="testuser_" + str(i) + "@unicef.org", password="un1c3f")
                user.is_staff = True
                user.save()
                userp = UserProfile.objects.get(user=user)
                country = Country.objects.get(name='uat')
                userp.country = country
                userp.country_override = country
                userp.save()

            if (numNewUsers > 0):
                self.stdout.write('Successfully created ' + str(numNewUsers) + ' new users')
            else:
                self.stdout.write('Please enter an integer greater than 0')
        except Exception as exp:
            raise CommandError(exp.message)