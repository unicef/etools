# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0064_auto_20160817_2233'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='partnerorganization',
            name='total_ct_cp',
        ),
        migrations.RemoveField(
            model_name='partnerorganization',
            name='total_ct_cy',
        ),
    ]
