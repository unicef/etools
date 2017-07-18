# -*- coding: utf-8 -*-
# Generated by Django 1.9.10 on 2017-07-03 15:18
from __future__ import unicode_literals

import django.contrib.postgres.fields
from django.db import migrations, models


MAP = {
    'Additional clause': 'Change in clause',
    'Amend existing clause': 'Change in clause'
}


def reverse(apps, schema_editor):
    pass
    # raise BaseException('Cannot migrate this backwards')


def migrate_amendment_types(apps, schema_editor):
    AgreementAmendment = apps.get_model('partners', 'AgreementAmendment')
    no = 0
    for agr in AgreementAmendment.objects.all():
        no += 1
        agr.types = [MAP.get(t.type, t.type) for t in agr.amendment_types.all()]
        agr.save()

    print 'Updated Agreements Amendments: {}'.format(no)


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0042_auto_20170707_2036'),
    ]

    operations = [
        migrations.AddField(
            model_name='agreementamendment',
            name='types',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(
                choices=[('Change IP name', 'Change in Legal Name of Implementing Partner'),
                         ('CP extension', 'Extension of Country Programme Cycle'),
                         ('Change authorized officer', 'Change Authorized Officer(s)'),
                         ('Change banking info', 'Banking Information'), ('Change in clause', 'Change in clause')],
                max_length=50), null=True, size=None),
        ),

        migrations.RunPython(
            migrate_amendment_types, reverse_code=reverse),

        migrations.AlterField(
            model_name='agreementamendment',
            name='types',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(
                choices=[('Change IP name', 'Change in Legal Name of Implementing Partner'),
                         ('CP extension', 'Extension of Country Programme Cycle'),
                         ('Change authorized officer', 'Change Authorized Officer(s)'),
                         ('Change banking info', 'Banking Information'), ('Change in clause', 'Change in clause')],
                max_length=50), size=None),
        ),
    ]
