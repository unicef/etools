# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0050_partnerorganization_shared_partner'),
    ]

    operations = [
        migrations.AlterField(
            model_name='resultchain',
            name='disaggregation',
            field=models.TextField(null=True),
        ),
    ]
