# Generated by Django 3.2.6 on 2022-07-18 10:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('field_monitoring_settings', '0007_auto_20200219_1036'),
    ]

    operations = [
        migrations.AlterField(
            model_name='option',
            name='label',
            field=models.CharField(max_length=100, verbose_name='Label'),
        ),
    ]