# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('et2f', '0014_auto_20161111_0125'),
    ]

    operations = [
        migrations.RenameField(
            model_name='travel',
            old_name='rejection_notice',
            new_name='rejection_note',
        ),
    ]
