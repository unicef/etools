import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('field_monitoring_planning', '0013_rename_dummy_models'),
        ('reports', '0001_initial'),
    ]

    operations = [
        # Add cp_output FK to EWPActivity
        migrations.AddField(
            model_name='ewpactivity',
            name='cp_output',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='ewp_activities',
                to='reports.result',
                verbose_name='CP Output',
            ),
        ),
        # Remove unique constraint on wbs alone
        migrations.AlterField(
            model_name='ewpactivity',
            name='wbs',
            field=models.CharField(max_length=255),
        ),
        # Add composite unique_together on (wbs, cp_output).
        # Note: the NULL case is handled by migration 0015 which replaces this
        # with proper partial UniqueConstraints.
        migrations.AlterUniqueTogether(
            name='ewpactivity',
            unique_together={('wbs', 'cp_output')},
        ),
        # Remove gpd FK from QuestionTemplate
        migrations.RemoveField(
            model_name='questiontemplate',
            name='gpd',
        ),
        # Remove gpds M2M from MonitoringActivity
        migrations.RemoveField(
            model_name='monitoringactivity',
            name='gpds',
        ),
        # Remove GPD model
        migrations.DeleteModel(
            name='GPD',
        ),
        # Update verbose_name on partners M2M
        migrations.AlterField(
            model_name='monitoringactivity',
            name='partners',
            field=models.ManyToManyField(
                blank=True,
                related_name='monitoring_activities',
                to='partners.partnerorganization',
                verbose_name='CSO Partner',
            ),
        ),
        # Update verbose_name on ewp_activities M2M
        migrations.AlterField(
            model_name='monitoringactivity',
            name='ewp_activities',
            field=models.ManyToManyField(
                blank=True,
                related_name='monitoring_activities',
                to='field_monitoring_planning.ewpactivity',
                verbose_name='Key Interventions',
            ),
        ),
    ]
