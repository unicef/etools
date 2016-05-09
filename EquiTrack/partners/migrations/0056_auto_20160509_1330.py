# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0055_auto_20160509_0934'),
    ]

    operations = [
        migrations.AddField(
            model_name='authorizedofficer',
            name='amendment',
            field=models.ForeignKey(blank=True, to='partners.AgreementAmendmentLog', null=True),
        ),
        migrations.AddField(
            model_name='bankdetails',
            name='amendment',
            field=models.ForeignKey(blank=True, to='partners.AgreementAmendmentLog', null=True),
        ),
    ]
