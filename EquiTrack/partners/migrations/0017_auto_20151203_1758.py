# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import smart_selects.db_fields


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0016_auto_20151126_1702'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pca',
            name='agreement',
            field=smart_selects.db_fields.ChainedForeignKey(chained_model_field=b'partner', related_name='interventions', chained_field=b'partner', blank=True, auto_choose=True, to='partners.Agreement', null=True),
        ),
    ]
