# -*- coding: utf-8 -*-
# Generated by Django 1.9.10 on 2017-09-15 17:35
from __future__ import unicode_literals

from django.db import migrations, models, connection, transaction


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_workspacecounter'),
        ('partners', '0056_intervention_sections'),
    ]

    def reverse(apps, schema_editor):
        pass

    @transaction.atomic
    def migrate_sector_location_links_to_intervention_section(apps, schema_editor):
        InterventionSectorLocationLink = apps.get_model('partners', 'InterventionSectorLocationLink')

        for interventionsector in InterventionSectorLocationLink.objects.all():
            intervention = interventionsector.intervention
            intervention.sections.add(interventionsector.sector)

    operations = [
        migrations.RunPython(migrate_sector_location_links_to_intervention_section, reverse_code=reverse)
    ]

