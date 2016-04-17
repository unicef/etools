# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0040_auto_20160411_1404'),
    ]

    operations = [
        migrations.AlterField(
            model_name='partnerorganization',
            name='name',
            field=models.CharField(help_text='Please make sure this matches the name you enter in VISION', max_length=255, verbose_name=b'Full Name'),
        ),
        migrations.AlterUniqueTogether(
            name='partnerorganization',
            unique_together=set([('name', 'vendor_number')]),
        ),
    ]
