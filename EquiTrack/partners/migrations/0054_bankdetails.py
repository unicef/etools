# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0053_auto_20160505_1810'),
    ]

    operations = [
        migrations.CreateModel(
            name='BankDetails',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('bank_name', models.CharField(max_length=255, null=True, blank=True)),
                ('bank_address', models.CharField(max_length=256L, blank=True)),
                ('account_title', models.CharField(max_length=255, null=True, blank=True)),
                ('account_number', models.CharField(max_length=50, null=True, blank=True)),
                ('routing_details', models.CharField(help_text=b'Routing Details, including SWIFT/IBAN (if applicable)', max_length=255, null=True, blank=True)),
                ('bank_contact_person', models.CharField(max_length=255, null=True, blank=True)),
                ('agreement', models.ForeignKey(related_name='bank_details', to='partners.Agreement')),
            ],
        ),
    ]
