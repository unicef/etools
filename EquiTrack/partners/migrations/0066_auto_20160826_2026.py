# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0065_auto_20160826_2024'),
    ]

    operations = [
        migrations.AddField(
            model_name='partnerorganization',
            name='total_ct_cp',
            field=models.DecimalField(help_text=b'Total Cash Transferred for Country Programme', null=True, max_digits=12, decimal_places=2, blank=True),
        ),
        migrations.AddField(
            model_name='partnerorganization',
            name='total_ct_cy',
            field=models.DecimalField(help_text=b'Total Cash Transferred per Current Year', null=True, max_digits=12, decimal_places=2, blank=True),
        ),
    ]
