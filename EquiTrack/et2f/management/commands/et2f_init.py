from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from et2f import PULI_USER_USERNAME, PULI_USER_PASSWORD
from users.models import Country


class Command(BaseCommand):
    def handle(self, *args, **options):
        User = get_user_model()

        if User.objects.filter(username=PULI_USER_USERNAME).exists():
            self.stdout.write('User already exists. Nothing to do')
            return

        uat_country = Country.objects.get(name='UAT')

        with atomic():
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