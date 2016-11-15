# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def move_boolean_to_choice(apps, schema_editor):
    REQUESTED = 'requested'
    NOT_REQUESTED = 'not_requested'
    NOT_APPLICABLE = 'not_applicable'
    
    Clearances = apps.get_model('et2f', 'Clearances')

    Clearances.objects.filter(medical_clearance=True).update(mc=REQUESTED)
    Clearances.objects.filter(medical_clearance=False).update(mc=NOT_REQUESTED)
    Clearances.objects.filter(medical_clearance=None).update(mc=NOT_APPLICABLE)

    Clearances.objects.filter(security_clearance=True).update(sc=REQUESTED)
    Clearances.objects.filter(security_clearance=False).update(sc=NOT_REQUESTED)
    Clearances.objects.filter(security_clearance=None).update(sc=NOT_APPLICABLE)

    Clearances.objects.filter(security_course=True).update(sco=REQUESTED)
    Clearances.objects.filter(security_course=False).update(sco=NOT_REQUESTED)
    Clearances.objects.filter(security_course=None).update(sco=NOT_APPLICABLE)


class Migration(migrations.Migration):

    dependencies = [
        ('et2f', '0017_auto_20161111_1230'),
    ]

    operations = [
        migrations.AddField(
            model_name='clearances',
            name='mc',
            field=models.CharField(default=b'not_applicable', max_length=14, choices=[(b'requested', b'requested'), (b'not_requested', b'not_requested'), (b'not_applicable', b'not_applicable')]),
        ),
        migrations.AddField(
            model_name='clearances',
            name='sc',
            field=models.CharField(default=b'not_applicable', max_length=14, choices=[(b'requested', b'requested'), (b'not_requested', b'not_requested'), (b'not_applicable', b'not_applicable')]),
        ),
        migrations.AddField(
            model_name='clearances',
            name='sco',
            field=models.CharField(default=b'not_applicable', max_length=14, choices=[(b'requested', b'requested'), (b'not_requested', b'not_requested'), (b'not_applicable', b'not_applicable')]),
        ),
        migrations.RunPython(move_boolean_to_choice),
    ]
