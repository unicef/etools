from __future__ import unicode_literals

from django.db import migrations


def fix_interventions(apps, schema):
    from etools.applications.partners.models import Intervention
    for i in Intervention.objects.all():
        try:
            i.save()
        except:
            print(i.reference_number, i.id, i.status)


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0025_auto_20180815_2026'),
    ]

    operations = [
        # Migration is commented out due to changes in model and subsequent
        # migrations needed to have run
        # migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop)
    ]
