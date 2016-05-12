# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def migrate_partners(apps, schema_editor):

    Trip = apps.get_model("trips", "Trip")
    LinkedPartner = apps.get_model("trips", "LinkedPartner")

    for trip in Trip.objects.all():

        for intervention in trip.pcas.all():
            link, created = LinkedPartner.objects.get_or_create(
                trip=trip,
                partner=intervention.partner,
                intervention=intervention
            )
            if created:
                print 'Linked Intervention {} to Trip {}'.format(
                    intervention.number, trip.id
                )


class Migration(migrations.Migration):

    dependencies = [
        ('trips', '0013_auto_20160428_1249'),
    ]

    operations = [
        migrations.RunPython(migrate_partners)
    ]
