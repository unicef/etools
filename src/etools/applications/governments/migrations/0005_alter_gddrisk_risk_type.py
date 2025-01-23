# Generated by Django 4.2.3 on 2025-01-23 15:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('governments', '0004_gdd_lead_section_alter_gdd_sections'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gddrisk',
            name='risk_type',
            field=models.CharField(choices=[('safeguarding', 'Safeguarding'), ('environment', 'Social and Environmental'), ('financial', 'Financial'), ('operational', 'Operational'), ('political', 'Political'), ('security', 'Safety and security')], max_length=50, verbose_name='Risk Type'),
        ),
    ]
