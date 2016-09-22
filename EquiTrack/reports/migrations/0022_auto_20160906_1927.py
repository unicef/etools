# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0021_auto_20160906_1925'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='indicator',
            unique_together=set([('name', 'result', 'sector')]),
        ),
        migrations.AlterUniqueTogether(
            name='result',
            unique_together=set([('wbs', 'country_programme')]),
        ),
        migrations.AlterUniqueTogether(
            name='resultstructure',
            unique_together=set([('name', 'from_date', 'to_date')]),
        ),
    ]
