# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django_fsm


class Migration(migrations.Migration):

    dependencies = [
        ('et2f', '0002_travel_hidden'),
    ]

    operations = [
        migrations.AlterField(
            model_name='travel',
            name='status',
            field=django_fsm.FSMField(default='planned', protected=True, max_length=50, choices=[('planned', 'Planned'), ('submitted', 'Submitted'), ('rejected', 'Rejected'), ('approved', 'Approved'), ('completed', 'Completed'), ('cancelled', 'Cancelled'), ('sent_for_payment', 'Sent for payment'), ('done', 'Done'), ('certification_submitted', 'Certification submitted'), ('certification_approved', 'Certification approved'), ('certification_rejected', 'Certification rejected'), ('certified', 'Certified'), ('completed', 'Completed')]),
        ),
    ]
