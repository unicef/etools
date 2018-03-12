# Models removed so that migration can run to drop the associated tables. Once
# that migration has been run on production, this entire app can be deleted and
# removed from INSTALLED_APPS.
from django.db import connection


# get_report_filename() is used in the trips initial migration.
def get_report_filename(instance, filename):
    return '/'.join([
        connection.schema_name,
        'trip_reports',
        str(instance.trip.id),
        filename
    ])
