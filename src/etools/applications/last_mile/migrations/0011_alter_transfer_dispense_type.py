# Generated by Django 4.2.3 on 2025-07-01 08:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('last_mile', '0010_remove_partnermaterial_description_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transfer',
            name='dispense_type',
            field=models.CharField(blank=True, choices=[('PHARMACY', 'Pharmacy'), ('MOBILE_OTP', 'Mobile OTP'), ('DISPENSING_UNIT', 'Dispensing Unit'), ('HOUSEHOLD_MOBILE_TEAM', 'Household Mobile Team'), ('OTHER', 'Other')], max_length=30, null=True),
        ),
    ]
