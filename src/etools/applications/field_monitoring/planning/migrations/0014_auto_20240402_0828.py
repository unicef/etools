# Generated by Django 3.2.19 on 2024-04-02 08:28

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('field_monitoring_planning', '0013_merge_0008_auto_20210108_1634_0012_auto_20210709_1455'),
    ]

    operations = [
        migrations.AddField(
            model_name='monitoringactivity',
            name='report_reviewer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='activities_to_review', to=settings.AUTH_USER_MODEL, verbose_name='Report Reviewer'),
        ),
        migrations.AddField(
            model_name='monitoringactivity',
            name='reviewed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='activities_reviewed', to=settings.AUTH_USER_MODEL, verbose_name='Reviewed By'),
        ),
        migrations.AddField(
            model_name='monitoringactivity',
            name='report_reviewer_preliminary',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Preliminary Report Reviewer'),
        ),
    ]
