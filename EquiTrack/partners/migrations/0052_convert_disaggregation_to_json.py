from __future__ import unicode_literals

from django.db import models, migrations


def updateResultChain(apps, schema_editor):
    """
        Make sure every user has their own countries available
    """

    ResultChain = apps.get_model("partners", "ResultChain")

    for rc in ResultChain.objects.all():

        if rc.disaggregation is not None:
            rc.disaggregation = '{' + rc.disaggregation.replace('=>', ':') + '}'

        rc.save()


def revert(apps, schema_editor):

    ResultChain = apps.get_model("partners", "ResultChain")

    for rc in ResultChain.objects.all():
        if rc.disaggregation == '{}':
            rc.disaggregation = None
        if rc.disaggregation is not None:
            rc.disaggregation = rc.disaggregation[1:-1].replace(':', '=>')

        rc.save()


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0051_auto_20160505_1740'),
    ]

    operations = [
        migrations.RunPython(updateResultChain, reverse_code=revert),
    ]
