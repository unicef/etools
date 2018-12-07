from django.db.models import Count, Q
from django.db import connection, models

from etools.applications.utils.common.utils import run_on_all_tenants
from unicef_locations.models import Location

def validate_database_locations():
    def _check_bad_database_locations():
        print("\n", connection.tenant.schema_name)

        if connection.tenant.schema_name != 'public':
            all_locations = Location.objects.all_locations()

            duplicate_locations = _get_duplicate_locations(all_locations)
            if duplicate_locations:
                print(len(duplicate_locations))
                print("duplicate_locations", duplicate_locations)

            empty_locations = _get_empty_locations(all_locations)
            if empty_locations:
                print(len(empty_locations))
                print("empty_locations", empty_locations)

    run_on_all_tenants(_check_bad_database_locations)

def fix_bad_database_locations():
    def _fix_bad_database_locations():
        if connection.tenant.schema_name != 'public':
            all_locations = Location.objects.all_locations()

            duplicate_locations = _get_duplicate_locations(all_locations)
            empty_locations = _get_empty_locations(all_locations)

            if duplicate_locations or empty_locations:
                print("\n")
                print(connection.tenant.schema_name)

            if empty_locations:
                print("empty_locations nr", len(empty_locations))
                print("empty_locations", empty_locations)
                if len(empty_locations) > 1:
                    for k, empty_pcode_loc in enumerate(empty_locations[1:]):
                        print("empty", k, empty_pcode_loc)
                        new_name = str(empty_pcode_loc.gateway) + " tempname " + str(k)
                        print("new name", new_name)
                        # empty_pcode_loc.name = new_name
                        # empty_pcode_loc.save()

            if duplicate_locations:
                print("duplicate_locations nr", len(duplicate_locations))
                print("duplicate_locations", duplicate_locations)
                if len(duplicate_locations) > 1:
                    for k, dupe in enumerate(duplicate_locations[1:], 1):
                        print("dupes", k, dupe)
                        new_pcode = dupe.p_code + "_temp_" + str(k)
                        print("new_pcode", new_pcode)
                        # dupe.p_code = new_pcode
                        # dupe.save()

    run_on_all_tenants(_fix_bad_database_locations)

def check_geom_pct_duplicates():
    def _check_geom_pct_duplicates():
        if connection.tenant.schema_name != 'public':
            all_locations = Location.objects.all_locations()
            dupes = all_locations.filter(Q(point__isnull=False) & Q(geom__isnull=False))
            if len(dupes) > 0:
                print("\n", connection.tenant.schema_name)
                print("Dupes nr:", print(len(dupes)))

    run_on_all_tenants(_check_geom_pct_duplicates)

def _get_duplicate_locations(locations_list):
    return locations_list.values('p_code') \
        .annotate(pcode_count=Count('p_code')) \
        .filter(pcode_count__gt=1)

def _get_empty_locations(locations_list):
    return locations_list.filter(
        Q(p_code__isnull=True) | Q(p_code='') |
        Q(name__isnull=True) | Q(name='')
    )
