# Generated by Django 2.2.8 on 2019-12-09 20:39
import json

from django.db import connection, migrations

from etools.libraries.pythonlib.encoders import CustomJSONEncoder


def update_partner_hact_json_structure(apps, schema_editor):

    # Only run this when NOT in test
    if connection.tenant.schema_name != "test":
        PartnerOrganization = apps.get_model("partners", "PartnerOrganization")
        for partner in PartnerOrganization.objects.all():
            hact = json.loads(partner.hact_values) if isinstance(partner.hact_values, str) else partner.hact_values
            hact['audits']['minimum_requirements'] = None
            hact['spot_checks']['minimum_requirements'] = None
            hact['programmatic_visits']['minimum_requirements'] = None
            partner.hact_values = json.dumps(hact, cls=CustomJSONEncoder)
            partner.save()


class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0040_auto_20191011_1429'),
    ]

    operations = [
        migrations.RunPython(update_partner_hact_json_structure, migrations.RunPython.noop),
    ]
