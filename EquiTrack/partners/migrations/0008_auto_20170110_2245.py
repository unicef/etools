# -*- coding: utf-8 -*-
# Generated by Django 1.9.10 on 2017-01-10 20:45
from __future__ import unicode_literals

from django.db import migrations, models


def reverse(apps, schema_editor):
    pass


def gov_int_copy_section_sectors(apps, schema_editor):
    GovernmentInterventionResult = apps.get_model('partners', 'GovernmentInterventionResult')
    for gir in GovernmentInterventionResult.objects.all():
        if gir.section:
            gir.sections.add(gir.section)
        if gir.sector:
            gir.sectors.add(gir.sector)
        gir.save()
        print('saved gir {}'.format(gir.id))

class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_userprofile_guid'),
        ('reports', '0003_auto_20161227_1953'),
        ('partners', '0007_auto_20170109_1840'),
    ]

    operations = [
        migrations.AddField(
            model_name='governmentinterventionresult',
            name='sections',
            field=models.ManyToManyField(blank=True, related_name='_governmentinterventionresult_sections_+', to='users.Section'),
        ),
        migrations.AddField(
            model_name='governmentinterventionresult',
            name='sectors',
            field=models.ManyToManyField(blank=True, related_name='_governmentinterventionresult_sectors_+', to='reports.Sector', verbose_name=b'Programme/Sector'),
        ),
        migrations.RunPython(
            gov_int_copy_section_sectors, reverse_code=reverse
        ),
        migrations.RemoveField(
            model_name='governmentinterventionresult',
            name='section',
        ),
        migrations.RemoveField(
            model_name='governmentinterventionresult',
            name='sector',
        ),
    ]
