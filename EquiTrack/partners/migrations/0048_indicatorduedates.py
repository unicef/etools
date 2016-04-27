# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0047_auto_20160427_2035'),
    ]

    operations = [
        migrations.CreateModel(
            name='IndicatorDueDates',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('due_date', models.DateField(null=True, blank=True)),
                ('intervention', models.ForeignKey(related_name='indicator_due_dates', blank=True, to='partners.PCA', null=True)),
            ],
        ),
    ]
