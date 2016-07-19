# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import smart_selects.db_fields


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0060_auto_20160715_0157'),
        ('trips', '0016_auto_20160607_2237'),
    ]

    operations = [
        migrations.CreateModel(
            name='LinkedGovernmentPartner',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('intervention', smart_selects.db_fields.ChainedForeignKey(chained_model_field=b'partner', related_name='trips', chained_field=b'partner', blank=True, auto_choose=True, to='partners.GovernmentIntervention', null=True)),
                ('partner', models.ForeignKey(to='partners.PartnerOrganization')),
                ('result', smart_selects.db_fields.ChainedForeignKey(chained_model_field=b'intervention', chained_field=b'intervention', blank=True, auto_choose=True, to='partners.GovernmentInterventionResult', null=True)),
                ('trip', models.ForeignKey(to='trips.Trip')),
            ],
        ),
    ]
