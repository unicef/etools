from django.contrib.gis.gdal import DataSource
from django.core.management.base import BaseCommand, CommandError

from locations.models import GatewayType, Location

location_mapping = {
    'name': 'ACS_NAME_1',
    'pcode': 'CERD',
    'longitude': 'X_Location',
    'latitude': 'Y_Location',
    'point': 'POINT',
}


class Command(BaseCommand):
    args = 'shapefile gateway_type'
    help = 'Import locations from UNICEF shape files'

    def handle(self, *args, **options):

        shape_file = args[0]
        gateway = args[1]
        skipped_points = []
        imported_points = 0

        try:

            gateway_type = GatewayType.objects.get(name=gateway)

            ds = DataSource(shape_file)
            self.stdout.write('{} Layers: {}'.format(ds, len(ds)))

            lyr = ds[0]
            self.stdout.write('Layer 1: {} {} {}'.format(lyr, len(lyr), lyr.geom_type))
            self.stdout.write(lyr.srs)

            self.stdout.write('Fields:')
            for field in lyr.fields:
                self.stdout.write(field)

            for feat in lyr:

                field_values = location_mapping.copy()
                for key, value in field_values.items():
                    field_values[key] = feat.get(value)

                if not field_values['p_code'] or field_values['p_code'] == '0':
                    self.stdout.write('No P_Code for location: {}'.format(field_values))
                    skipped_points.append(field_values)
                    continue

                self.stdout.write("\nImporting values: {}".format(field_values))

                location, created = Location.objects.get_or_create(
                    name=field_values['name'].encode('utf-8'),
                    gateway=gateway_type,
                )
                location.name = field_values['name'].encode('utf-8')
                location.p_code = str(field_values['p_code'])
                location.longitude = field_values['longitude']
                location.latitude = field_values['latitude']
                location.point = feat.geom.wkt
                location.save()

                self.stdout.write("Location {} {}".format(
                    location.name,
                    "created" if created else 'updated'
                ))
                imported_points += 1

        except Exception as exp:
            raise CommandError(exp)

        self.stdout.write("{} points skipped".format(len(skipped_points)))
        self.stdout.write("{} points imported".format(imported_points))
