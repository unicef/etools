# Generated by Django 1.10.8 on 2018-11-02 16:20
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attachments', '0012_attachmentflat_source'),
    ]

    operations = [
        migrations.AddField(
            model_name='attachmentflat',
            name='pd_ssfa',
            field=models.IntegerField(blank=True, null=True, verbose_name='PD SSFA ID'),
        ),
    ]
