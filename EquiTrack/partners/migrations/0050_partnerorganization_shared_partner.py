# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0049_auto_20160428_0213'),
    ]

    operations = [
        migrations.AddField(
            model_name='partnerorganization',
            name='shared_partner',
            field=models.CharField(default='No', help_text='Partner shared with UNDP or UNFPA?', max_length=50, choices=[('No', 'No'), ('with UNDP', 'with UNDP'), ('with UNFPA', 'with UNFPA'), ('with UNDP & UNFPA', 'with UNDP & UNFPA')]),
        ),
    ]
