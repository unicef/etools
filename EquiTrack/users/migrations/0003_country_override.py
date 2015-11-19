from __future__ import unicode_literals

from django.db import models, migrations


def updateCountryOverride(apps, schema_editor):
    "transform all vote field from choice Model to a vote model with root user as owner"

    UserProfile = apps.get_model("users", "UserProfile")
    for profile in UserProfile.objects.all():
        if profile.country.name == "UAT":
            profile.country_override = profile.country
            profile.save()



def revert(apps, schema_editor):

    raise RuntimeError("reversing this migration not possible")


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_userprofile_country_override'),
    ]

    operations = [
        migrations.RunPython(updateCountryOverride, reverse_code=revert),
    ]
