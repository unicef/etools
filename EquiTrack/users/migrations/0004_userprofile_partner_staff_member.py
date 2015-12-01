# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_country_override'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='partner_staff_member',
            field=models.IntegerField(null=True, blank=True),
        ),
    ]
