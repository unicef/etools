# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0011_auto_20151102_2052'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pca',
            name='partnership_type',
            field=models.CharField(default='pd', choices=[('pd', 'Programme Document'), ('shpd', 'Simplified Humanitarian Programme Document'), ('dct', 'Cash Transfers to Government'), ('ssfa', 'SSFA TOR'), ('ic', 'IC TOR')], max_length=255, blank=True, null=True, verbose_name='Document type'),
            preserve_default=True,
        ),
    ]
