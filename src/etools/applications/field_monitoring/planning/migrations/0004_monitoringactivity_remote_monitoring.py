# Generated by Django 4.2.3 on 2024-08-13 03:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('field_monitoring_planning', '0003_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='monitoringactivity',
            name='remote_monitoring',
            field=models.BooleanField(default=False, verbose_name='Involves Remote Monitoring'),
        ),
    ]
