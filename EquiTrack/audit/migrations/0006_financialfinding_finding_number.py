# -*- coding: utf-8 -*-
# Generated by Django 1.9.10 on 2017-07-13 14:42
from __future__ import unicode_literals

from collections import Counter

from django.db import migrations, models


def set_finding_numbers(apps, schema_editor):
    FinancialFinding = apps.get_model('audit', 'FinancialFinding')
    Finding = apps.get_model('audit', 'Finding')

    finding_counter = Counter()
    for finding in FinancialFinding.objects.all():
        finding_counter[finding.audit_id] += 1

        finding.finding_number = finding_counter[finding.audit_id]
        finding.save()

    finding_counter = Counter()
    for finding in Finding.objects.all():
        finding_counter[finding.spot_check_id] += 1

        finding.finding_number = finding_counter[finding.spot_check_id]
        finding.save()


def do_nothing(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0005_merge'),
    ]

    operations = [
        migrations.AddField(
            model_name='financialfinding',
            name='finding_number',
            field=models.PositiveIntegerField(default=1, editable=False, verbose_name='Finding Number'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='finding',
            name='finding_number',
            field=models.PositiveIntegerField(default=1, editable=False, verbose_name='Finding number'),
            preserve_default=False,
        ),
        migrations.RunPython(
            set_finding_numbers,
            do_nothing,
        ),
    ]
