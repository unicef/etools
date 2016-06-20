# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import smart_selects.db_fields


class Migration(migrations.Migration):

    dependencies = [
        ('trips', '0014_auto_20160510_1432'),
    ]

    operations = [
        migrations.AlterField(
            model_name='linkedpartner',
            name='result',
            field=smart_selects.db_fields.ChainedForeignKey(chained_model_field=b'intervention', chained_field=b'intervention', blank=True, auto_choose=True, to='partners.RAMIndicator', null=True),
        ),
    ]
