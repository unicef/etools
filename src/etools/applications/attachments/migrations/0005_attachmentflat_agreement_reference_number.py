# Generated by Django 1.10.8 on 2018-06-06 10:29
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attachments', '0004_make_not_nullable'),
    ]

    operations = [
        migrations.AddField(
            model_name='attachmentflat',
            name='agreement_reference_number',
            field=models.CharField(blank=True, max_length=100, verbose_name='Agreement Reference Number'),
        ),
    ]
