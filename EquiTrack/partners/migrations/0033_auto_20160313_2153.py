# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0032_pca_project_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='partnerorganization',
            name='rating',
            field=models.CharField(max_length=50, null=True, verbose_name='Risk Rating'),
        ),
    ]
