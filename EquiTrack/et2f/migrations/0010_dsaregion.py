# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('et2f', '0009_auto_20161109_1623'),
    ]

    operations = [
        migrations.CreateModel(
            name='DSARegion',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('dsa_amount_usd', models.DecimalField(max_digits=20, decimal_places=4)),
                ('dsa_amount_60plus_usd', models.DecimalField(max_digits=20, decimal_places=4)),
                ('dsa_amount_local', models.DecimalField(max_digits=20, decimal_places=4)),
                ('dsa_amount_60plus_local', models.DecimalField(max_digits=20, decimal_places=4)),
                ('room_rate', models.DecimalField(max_digits=20, decimal_places=4)),
            ],
        ),
    ]
