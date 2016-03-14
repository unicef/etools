# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import smart_selects.db_fields


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0014_auto_20160314_0319'),
        ('partners', '0033_auto_20160313_2153'),
    ]

    operations = [
        migrations.CreateModel(
            name='RAMIndicator',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('indicator', smart_selects.db_fields.ChainedForeignKey(chained_model_field=b'result', to='reports.Indicator', chained_field=b'result', auto_choose=True)),
                ('intervention', models.ForeignKey(related_name='indicators', to='partners.PCA')),
                ('result', models.ForeignKey(to='reports.Result')),
            ],
        ),
    ]
