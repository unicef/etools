# Generated by Django 4.2.3 on 2024-10-18 01:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('governments', '0009_ewpactivity_end_date_ewpactivity_other_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='ewpactivity',
            old_name='wpa_wbs',
            new_name='wbs',
        ),
    ]
