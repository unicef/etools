# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import smart_selects.db_fields


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0069_auto_20160915_2222'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ramindicator',
            name='indicator',
            field=smart_selects.db_fields.ChainedForeignKey(chained_model_field=b'result', chained_field=b'result', blank=True, auto_choose=True, to='reports.Indicator', null=True),
        ),
    ]
