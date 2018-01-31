from __future__ import unicode_literals, print_function

from django.db import migrations, models, connection
import django.db.models.deletion
import django.utils.timezone
from django.contrib.gis.geos import GEOSGeometry
import model_utils.fields
import mptt.fields
from django.db.models import Q


def myprint(*args):
    print(*args)
    file_name = 'migration_reports_0015.txt'
    args_list = [unicode(arg) for arg in args]
    with open(file_name, 'ab') as f:
        f.write(', '.join(args_list))
        f.write('\n')


def finalize_migrations(apps, schema_editor):
    # AppliedIndicator = apps.get_model('reports', 'AppliedIndicator')
    # Location = apps.get_model('locations', 'Location')
    # GatewayType = apps.get_model('locations', 'GatewayType')
    from locations.models import Location, GatewayType
    from reports.models import AppliedIndicator

    try:
        admin0 = GatewayType.objects.get_or_create(admin_level=0,
                                                   defaults={'name': 'Country'})[0]
    except django.db.utils.IntegrityError:
        admin0 = GatewayType.objects.get(name='Country')
        admin0.admin_level = 0
        # TODO: Raise these
        # assert admin0.location_set.all().count() <= 1
        admin0.save()

    try:
        admin0_location = Location.objects.get(gateway__pk=admin0.pk)

    except Location.DoesNotExist:
        myprint('Creating a default location for the country ', connection.schema_name)
        admin0_location = Location()
        admin0_location.name = connection.schema_name.title()
        admin0_location.p_code = connection.schema_name
        admin0_location.point = GEOSGeometry('POINT(-96.876369 29.905320)')
        admin0_location.gateway = admin0
        admin0_location.save()

    except Location.MultipleObjectsReturned:
        # TODO: Not sure if this should be handled some other way, genevapfp
        admin0_location = Location.objects.filter(gateway__pk=admin0.pk).first()

    # add section to applied indicator
    ainds = AppliedIndicator.objects.prefetch_related('lower_result__result_link__intervention').all()

    myprint('number of indicators to update: ', ainds.count())

    for aind in ainds:
        intervention = aind.lower_result.result_link.intervention

        intervention_sections = intervention.sections.count()
        if intervention_sections > 1:
            myprint('multiple sections for this pd ', ' '.join(unicode(i) for i in [
                'id', intervention.id,
                'number', intervention.number,
                'status', intervention.status,
                'indicator_id', aind.id,
                #'indicator', aind.indicator.title,
            ]))
            # TODO: Raise these
            # raise Exception("this intervention has more than 1 section")
        elif intervention_sections < 1:
            myprint('no sections for this pd ', ' '.join(unicode(i) for i in[
                'id', intervention.id,
                'number', intervention.number,
                'status', intervention.status,
                'indicator_id', aind.id,
                #'indicator', aind.indicator.title,
            ]))
            # raise Exception("this intervention has no section")

        section = intervention.sections.first()
        aind.section = section
        aind.save()

        # add locations to applied indicator
        intervention.flat_locations.add(admin0_location)
        aind.locations.add(admin0_location)


class Migration(migrations.Migration):

    dependencies = [
        ('locations', '0006_auto_20171024_1011'),
        ('reports', '0016_indicators'),
        ('partners', '0058_intervention_locations'),
    ]

    operations = [
        migrations.RunPython(finalize_migrations, reverse_code=migrations.RunPython.noop)
    ]