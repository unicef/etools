# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_userprofile_partner_staff_member'),
    ]

    operations = [
        migrations.AddField(
            model_name='country',
            name='buisness_area_code',
            field=models.IntegerField(default=0),
        ),
    ]
