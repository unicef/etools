import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('action_points', '0003_actionpointcomment'),
        ('field_monitoring_planning', '0014_remove_gpd_add_ewpactivity_cp_output'),
    ]

    operations = [
        migrations.AddField(
            model_name='actionpoint',
            name='ewp_activity',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='field_monitoring_planning.ewpactivity',
                verbose_name='KI/Activity',
            ),
        ),
    ]
