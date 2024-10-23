# Generated by Django 4.2.3 on 2024-10-15 14:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('governments', '0003_rename_cp_output_governmentewp_country_programme'),
    ]

    operations = [
        migrations.RenameField(
            model_name='governmentewp',
            old_name='plan_category_type',
            new_name='category_type',
        ),
        migrations.RemoveField(
            model_name='ewpactivity',
            name='wpa_gid',
        ),
        migrations.RemoveField(
            model_name='governmentewp',
            name='workplan_gid',
        ),
        migrations.AddField(
            model_name='ewpactivity',
            name='wpa_wbs',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='Workplan Activity WBS'),
        ),
        migrations.AddField(
            model_name='governmentewp',
            name='workplan_wbs',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='Workplan WBS'),
        ),
    ]