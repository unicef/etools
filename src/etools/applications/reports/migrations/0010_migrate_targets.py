from django.db import migrations, models


def update_targets(apps, schema_editor):
    AppliedIndicator = apps.get_model("reports", "AppliedIndicator")
    ais = AppliedIndicator.objects.prefetch_related('indicator').all()

    for ai in ais:
        ai.target_new['v'] = ai.target
        ai.baseline_new['v'] = ai.baseline
        if ai.indicator.unit != 'number':
            ai.target_new['d'] = 100
            ai.baseline_new['d'] = 100

        ai.save()


def reverse(apps, schema_editor):
    AppliedIndicator = apps.get_model("reports", "AppliedIndicator")
    ais = AppliedIndicator.objects.prefetch_related('indicator').all()

    for ai in ais:
        ai.target = ai.target_new['v']
        ai.baseline = ai.baseline_new['v']
        ai.save()


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0009_auto_20180606_1807'),
    ]

    operations = [
        migrations.RunPython(update_targets, reverse_code=reverse)
    ]
