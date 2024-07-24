# Generated by Django 3.2.19 on 2024-07-19 11:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('field_monitoring_settings', '0001_initial'),
        ('reports', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='sections',
            field=models.ManyToManyField(blank=True, to='reports.Section', verbose_name='Sections'),
        ),
        migrations.AddField(
            model_name='option',
            name='question',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='options', to='field_monitoring_settings.question', verbose_name='Question'),
        ),
    ]
