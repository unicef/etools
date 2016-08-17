# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0063_auto_20160817_2202'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fundingcommitment',
            name='agreement_amount',
            field=models.DecimalField(null=True, max_digits=12, decimal_places=2, blank=True),
        ),
        migrations.AlterField(
            model_name='fundingcommitment',
            name='commitment_amount',
            field=models.DecimalField(null=True, max_digits=12, decimal_places=2, blank=True),
        ),
        migrations.AlterField(
            model_name='fundingcommitment',
            name='expenditure_amount',
            field=models.DecimalField(null=True, max_digits=12, decimal_places=2, blank=True),
        ),
        migrations.AlterField(
            model_name='fundingcommitment',
            name='fr_item_amount_usd',
            field=models.DecimalField(null=True, max_digits=12, decimal_places=2, blank=True),
        ),
    ]
