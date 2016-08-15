# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import smart_selects.db_fields


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0060_auto_20160721_2313'),
        ('trips', '0017_linkedgovernmentpartner'),
    ]

    operations = [
        migrations.AddField(
            model_name='linkedpartner',
            name='result',
            field=smart_selects.db_fields.ChainedForeignKey(chained_model_field=b'partnership', chained_field=b'intervention', blank=True, auto_choose=True, to='partners.ResultChain', null=True),
        ),
    ]
