# Generated manually for is_programatic_visit database field

from django.db import migrations, models


def backfill_is_programatic_visit(apps, schema_editor):
    """Set is_programatic_visit for existing completed activities."""
    MonitoringActivity = apps.get_model('field_monitoring_planning', 'MonitoringActivity')
    ActivityQuestionOverallFinding = apps.get_model(
        'field_monitoring_data_collection', 'ActivityQuestionOverallFinding'
    )
    ActivityOverallFinding = apps.get_model(
        'field_monitoring_data_collection', 'ActivityOverallFinding'
    )
    ActivityQuestion = apps.get_model('field_monitoring_data_collection', 'ActivityQuestion')

    completed = MonitoringActivity.objects.filter(status='completed')
    for activity in completed:
        if not activity.start_date or not activity.end_date:
            MonitoringActivity.objects.filter(pk=activity.pk).update(is_programatic_visit=False)
            continue
        if activity.start_date.year != activity.end_date.year:
            MonitoringActivity.objects.filter(pk=activity.pk).update(is_programatic_visit=False)
            continue

        hact_question_ids = ActivityQuestion.objects.filter(
            monitoring_activity_id=activity.pk,
            is_hact=True,
        ).values_list('id', flat=True)
        hact_answered = ActivityQuestionOverallFinding.objects.filter(
            activity_question_id__in=hact_question_ids,
            value__isnull=False,
        ).exists()
        on_track_answered = ActivityOverallFinding.objects.filter(
            monitoring_activity_id=activity.pk,
            on_track__isnull=False,
        ).exists()
        new_value = hact_answered and on_track_answered
        MonitoringActivity.objects.filter(pk=activity.pk).update(is_programatic_visit=new_value)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('field_monitoring_planning', '0011_add_completion_date_to_monitoring_activity'),
    ]

    operations = [
        migrations.AddField(
            model_name='monitoringactivity',
            name='is_programatic_visit',
            field=models.BooleanField(
                default=False,
                help_text='True when status is completed, start/end date are in the same year, HACT question is answered, and summary on-track is answered.',
                verbose_name='Programmatic Visit',
            ),
        ),
        migrations.RunPython(backfill_is_programatic_visit, noop_reverse),
    ]
