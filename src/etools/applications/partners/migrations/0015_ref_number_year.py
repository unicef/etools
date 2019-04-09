from __future__ import unicode_literals

from django.db import migrations, models


def populate_agreement_ref_num(apps, schema):
    import re
    from django.db import IntegrityError

    Agreement = apps.get_model("partners", "Agreement")

    for a in Agreement.view_objects.all():
        find = re.findall(r'\d{4}', a.agreement_number)
        try:
            ref_number_str = find[0]
            a.reference_number_year = int(ref_number_str)
            assert 1950 < a.reference_number_year < 2100
            a.save()
        except IntegrityError:
            if a.status in ['Signed', 'Suspended']:
                raise
                # otherwise we don't care
        except (IndexError, AssertionError):
            # could not find a reference number:
            if a.status in ['Signed', 'Suspended']:
                raise


def populate_intervention_ref_num(apps, schema):
    import re
    from django.db import IntegrityError
    Intervention = apps.get_model("partners", "Intervention")

    for i in Intervention.objects.exclude(document_type="SSFA"):
        find = re.findall(r'\d{4}', i.number)
        try:
            ref_number_str = find[0]
            i.reference_number_year = int(ref_number_str)
            assert 1950 < i.reference_number_year < 2100
            i.save()
        except IntegrityError:
            if i.status in ['Signed', 'Active', 'Suspended', 'Ended']:
                raise
                # otherwise we don't care
        except (IndexError, AssertionError):
            # could not find a reference number:
            if i.status in ['Signed', 'Active', 'Suspended', 'Ended']:
                raise

class Migration(migrations.Migration):

    dependencies = [
        ('partners', '0014_auto_20180716_1547'),
    ]

    operations = [
        # migrations.AlterModelManagers(name='Agreement', managers=['objects', models.manager.Manager()]),
        # migrations.AlterModelManagers(name='Intervention', managers=['objects', models.manager.Manager()]),
        migrations.RunPython(populate_agreement_ref_num, reverse_code=migrations.RunPython.noop),
        migrations.RunPython(populate_intervention_ref_num, reverse_code=migrations.RunPython.noop)
    ]
