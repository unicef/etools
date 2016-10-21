# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0072_partnerorganization_hact_values'),
    ]

    operations = [
        migrations.AddField(
            model_name='governmentinterventionresult',
            name='planned_visits',
            field=models.IntegerField(default=0),
        ),
    ]
