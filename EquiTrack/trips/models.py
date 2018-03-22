from __future__ import absolute_import, division, print_function, unicode_literals

# Models removed so that migration can run to drop the associated tables. Once
# that migration has been run on production, this entire app can be deleted and
# removed from INSTALLED_APPS.
from django.db import connection
from django.utils import six


# get_report_filename() is used in the trips initial migration.
def get_report_filename(instance, filename):
    return '/'.join([
        connection.schema_name,
        'trip_reports',
        six.text_type(instance.trip.id),
        filename
    ])
