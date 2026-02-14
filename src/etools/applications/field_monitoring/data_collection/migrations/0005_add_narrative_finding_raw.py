# Generated manually on 2026-02-12
# Add narrative_finding_raw field to store raw text with formatting tags

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('field_monitoring_data_collection', '0004_fix_gpd_foreign_key'),
    ]

    operations = [
        migrations.AddField(
            model_name='activityoverallfinding',
            name='narrative_finding_raw',
            field=models.TextField(blank=True, verbose_name='Narrative Finding Raw'),
        ),
        migrations.AddField(
            model_name='checklistoverallfinding',
            name='narrative_finding_raw',
            field=models.TextField(blank=True, verbose_name='Narrative Finding Raw'),
        ),
    ]
