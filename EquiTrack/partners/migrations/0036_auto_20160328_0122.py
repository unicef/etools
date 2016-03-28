# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0035_auto_20160314_1524'),
    ]

    operations = [
        migrations.AddField(
            model_name='fundingcommitment',
            name='end',
            field=models.DateTimeField(null=True, verbose_name='end', blank=True),
        ),
        migrations.AddField(
            model_name='fundingcommitment',
            name='start',
            field=models.DateTimeField(null=True, verbose_name='start', blank=True),
        ),
        migrations.AlterField(
            model_name='fundingcommitment',
            name='intervention',
            field=models.ForeignKey(related_name='funding_commitments', to='partners.PCA', null=True),
        ),
        migrations.AlterField(
            model_name='pca',
            name='partner',
            field=models.ForeignKey(related_name='documents', to='partners.PartnerOrganization'),
        ),
    ]
