from __future__ import unicode_literals

from django.db import models, migrations


def updateCountriesAvailable(apps, schema_editor):
    """
        Make sure every user has their own countries available
    """

    UserProfile = apps.get_model("users", "UserProfile")
    Country = apps.get_model("users", "Country")
    countries = Country.objects.all()

    for profile in UserProfile.objects.all():
        if profile.user.is_superuser:
            # for superusers add all countries
            profile.countries_available = [c for c in countries]

        elif profile.user.is_staff and \
                profile.country:
            profile.countries_available.add(profile.country)

        profile.save()


def revert(apps, schema_editor):

    raise RuntimeError("reversing this migration not possible")


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_userprofile_countries_available'),
    ]

    operations = [
        migrations.RunPython(updateCountriesAvailable, reverse_code=revert),
    ]
