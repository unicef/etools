# -*- coding: utf-8 -*-
# Generated by Django 1.9.10 on 2018-02-16 20:39
from __future__ import unicode_literals

from django.db import migrations, transaction


@transaction.atomic
def create_planned_engagements(apps, schema_editor):
    PartnerOrganization = apps.get_model('partners', 'PartnerOrganization')
    PlannedEngagement = apps.get_model('partners', 'PlannedEngagement')
    for partner in PartnerOrganization.objects.all():
        PlannedEngagement.objects.get_or_create(partner=partner)


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0060_auto_20180216_2027'),
    ]

    operations = [
    ]

    operations = [
        migrations.RunPython(create_planned_engagements, reverse_code=migrations.RunPython.noop)
    ]



