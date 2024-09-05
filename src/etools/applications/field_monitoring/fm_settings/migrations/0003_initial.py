# Generated by Django 3.2.19 on 2024-07-19 11:57

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('partners', '0001_initial'),
        ('reports', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('field_monitoring_settings', '0002_initial'),
        ('locations', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='logissue',
            name='author',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_logissues', to=settings.AUTH_USER_MODEL, verbose_name='Issue Raised By'),
        ),
        migrations.AddField(
            model_name='logissue',
            name='cp_output',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='log_issues', to='reports.result', verbose_name='CP Output'),
        ),
        migrations.AddField(
            model_name='logissue',
            name='location',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='log_issues', to='locations.location', verbose_name='Location'),
        ),
        migrations.AddField(
            model_name='logissue',
            name='location_site',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='log_issues', to='field_monitoring_settings.locationsite', verbose_name='Site'),
        ),
        migrations.AddField(
            model_name='logissue',
            name='partner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='log_issues', to='partners.partnerorganization', verbose_name='Partner'),
        ),
        migrations.AddField(
            model_name='locationsite',
            name='parent',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sites', to='locations.location', verbose_name='Parent Location'),
        ),
        migrations.AlterUniqueTogether(
            name='option',
            unique_together={('question', 'value')},
        ),
    ]