# Generated by Django 2.2.4 on 2019-10-11 13:03

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0021_auto_20191011_1201'),
        ('action_points', '0011_actionpoint_reference_number'),
    ]

    operations = [
        migrations.AlterField(
            model_name='actionpoint',
            name='office',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='reports.Office', verbose_name='Office'),
        ),
    ]
