# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0061_partnerorganization_hidden'),
    ]

    operations = [
        migrations.AddField(
            model_name='partnerorganization',
            name='deleted_flag',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='partnerorganization',
            name='total_ct_cp',
            field=models.PositiveIntegerField(help_text=b'Total Cash Transferred for Country Programme', null=True, blank=True),
        ),
        migrations.AddField(
            model_name='partnerorganization',
            name='total_ct_cy',
            field=models.PositiveIntegerField(help_text=b'Total Cash Transferred per Current Year', null=True, blank=True),
        ),
    ]
