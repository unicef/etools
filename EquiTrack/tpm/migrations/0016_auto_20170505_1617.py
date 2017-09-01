# -*- coding: utf-8 -*-
# Generated by Django 1.9.10 on 2017-05-05 16:17
from __future__ import unicode_literals

from django.db import migrations


def create_email_templates(apps, schema_editor):
    EmailTemplate = apps.get_model('post_office', 'EmailTemplate')

    EmailTemplate.objects.get_or_create(name='tpm/visit/assign')
    EmailTemplate.objects.get_or_create(name='tpm/visit/reject')
    EmailTemplate.objects.get_or_create(name='tpm/visit/accept')
    EmailTemplate.objects.get_or_create(name='tpm/visit/generate_report')
    EmailTemplate.objects.get_or_create(name='tpm/visit/report')
    EmailTemplate.objects.get_or_create(name='tpm/visit/approve_report')
    EmailTemplate.objects.get_or_create(name='tpm/visit/approve_report_tpm')


def do_nothing(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('tpm', '0015_auto_20170502_0953'),
        ('post_office', '0004_auto_20160607_0901'),
    ]

    operations = [
        migrations.RunPython(
            create_email_templates,
            do_nothing,
        ),
    ]
