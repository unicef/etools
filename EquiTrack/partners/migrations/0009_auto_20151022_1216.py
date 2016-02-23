# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0008_auto_20151018_2238'),
    ]

    operations = [
        migrations.AlterField(
            model_name='partnerorganization',
            name='type',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='CSO Type', choices=[('International NGO', 'International NGO'), ('National NGO', 'National NGO'), ('CBO', 'CBO'), ('Academic Institution', 'Academic Institution')]),
            preserve_default=True,
        ),
    ]
