from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    """
    Replace the composite unique_together on EWPActivity(wbs, cp_output) with two
    partial UniqueConstraints so that the NULL cp_output case is also enforced.

    In PostgreSQL, a standard UNIQUE constraint treats NULL as distinct from NULL,
    meaning two rows with (wbs='x', cp_output=NULL) would both satisfy the old
    constraint.  The partial indexes below close that gap.
    """

    dependencies = [
        ('field_monitoring_planning', '0014_remove_gpd_add_ewpactivity_cp_output'),
    ]

    operations = [
        # Remove the composite unique_together that migration 0014 created.
        migrations.AlterUniqueTogether(
            name='ewpactivity',
            unique_together=set(),
        ),
        # (wbs, cp_output) uniqueness when cp_output IS NOT NULL.
        migrations.AddConstraint(
            model_name='ewpactivity',
            constraint=models.UniqueConstraint(
                fields=['wbs', 'cp_output'],
                condition=Q(cp_output__isnull=False),
                name='unique_ewpactivity_wbs_cp_output',
            ),
        ),
        # wbs uniqueness when cp_output IS NULL.
        migrations.AddConstraint(
            model_name='ewpactivity',
            constraint=models.UniqueConstraint(
                fields=['wbs'],
                condition=Q(cp_output__isnull=True),
                name='unique_ewpactivity_wbs_null_cp_output',
            ),
        ),
    ]
