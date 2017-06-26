# -*- coding: utf-8 -*-
# Generated by Django 1.9.10 on 2017-05-11 11:56
from __future__ import unicode_literals

from django.db import migrations, models


CHOICES = [
    ('unicef_focal_point', 'UNICEF Focal Point'),
    ('pme', 'Planning, Monitoring & Evaluation'),
    ('third_party_monitor', 'Third Party Monitor'),
    ('unicef_user', 'UNICEF User'),
]


def migrate_choices(apps, scheme_editor):
    TPMPermission = apps.get_model('tpm', 'TPMPermission')

    for choice in CHOICES:
        TPMPermission.objects.filter(user_type=choice[1]).update(user_type=choice[0])


def backward_choices(apps, scheme_editor):
    TPMPermission = apps.get_model('tpm', 'TPMPermission')

    for choice in CHOICES:
        TPMPermission.objects.filter(user_type=choice[1]).update(user_type=choice[0])


class Migration(migrations.Migration):

    dependencies = [
        ('tpm', '0017_merge'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tpmpermission',
            name='user_type',
            field=models.CharField(choices=[('unicef_focal_point', 'UNICEF Focal Point'), ('pme', 'PME'), ('third_party_monitor', 'Third Party Monitor'), ('unicef_user', 'UNICEF User')], max_length=30),
        ),
    ]
