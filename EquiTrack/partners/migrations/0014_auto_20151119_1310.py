# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0013_auto_20151118_1151'),
    ]

    operations = [
        migrations.AlterField(
            model_name='agreement',
            name='agreement_type',
            field=models.CharField(max_length=10, choices=[('PCA', 'Programme Cooperation Agreement'), ('SSFA', 'Small Scale Funding Agreement'), ('MOU', 'Memorandum of Understanding'), ('IC', 'Institutional Contract'), ('AWP', 'Work Plan')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='pca',
            name='partnership_type',
            field=models.CharField(default='PD', choices=[('PD', 'Programme Document'), ('SHPD', 'Simplified Humanitarian Programme Document'), ('AWP', 'Cash Transfers to Government'), ('SSFA', 'SSFA TOR'), ('IC', 'IC TOR')], max_length=255, blank=True, null=True, verbose_name='Document type'),
            preserve_default=True,
        ),
    ]
