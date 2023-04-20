# Generated by Django 3.2.6 on 2023-04-17 09:36

from django.db import migrations, models
import etools.applications.audit.models


class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0024_audit_year_of_audit'),
    ]

    operations = [
        migrations.AlterField(
            model_name='engagement',
            name='year_of_audit',
            field=models.PositiveSmallIntegerField(db_index=True, default=etools.applications.audit.models.get_current_year, null=True),
        ),
    ]