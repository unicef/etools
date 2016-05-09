# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0054_bankdetails'),
    ]

    operations = [
        migrations.AlterField(
            model_name='partnerorganization',
            name='email',
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='partnerorganization',
            name='phone_number',
            field=models.CharField(max_length=32L, null=True, blank=True),
        ),
    ]
