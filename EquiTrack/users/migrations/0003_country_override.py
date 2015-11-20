from __future__ import unicode_literals

from django.db import models, migrations


def updateCountryOverride(apps, schema_editor):

    UserProfile = apps.get_model("users", "UserProfile")
    for profile in UserProfile.objects.all():
        if profile.country and profile.country.name == "UAT":
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
