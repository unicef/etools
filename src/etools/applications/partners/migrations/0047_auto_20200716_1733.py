# Generated by Django 2.2.7 on 2020-07-16 17:33

from django.db import migrations
import django_fsm


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0046_interventionactivity_interventionactivityitem_interventionactivitytimeframe_interventionmanagementbu'),
    ]

    operations = [
        migrations.AlterField(
            model_name='intervention',
            name='status',
            field=django_fsm.FSMField(blank=True, choices=[('draft', 'Draft'), ('development', 'Development'), ('signed', 'Signed'), ('active', 'Active'), ('ended', 'Ended'), ('closed', 'Closed'), ('suspended', 'Suspended'), ('terminated', 'Terminated')], default='development', max_length=32, verbose_name='Status'),
        ),
    ]
