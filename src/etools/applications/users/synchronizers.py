import json


from etools.applications.users.models import Country
from etools.applications.vision.synchronizers import VisionDataTenantSynchronizer


class CountryLongNameSync(VisionDataTenantSynchronizer):
    ENDPOINT = 'GetBusinessAreaList_JSON'
    GLOBAL_CALL = True

    def __init__(self, *args, **kwargs):
        self.countries_qs = Country.objects.exclude(business_area_code='0')
        super().__init__(*args, **kwargs)

    def _convert_records(self, records):
        records = json.loads(records['GetBusinessAreaList_JSONResult'])
        records = dict((r['BUSINESS_AREA_CODE'], r) for r in records)
        return records

    def _save_records(self, records):
        countries = self.countries_qs.all()
        countries_updated = []
        for c in countries:
            try:
                new_name = records[c.business_area_code]['BUSINESS_AREA_LONG_NAME']
            except KeyError:
                continue
            if c.long_name != new_name:
                countries_updated.append((c.business_area_code, c.name, c.long_name, new_name))
                c.long_name = new_name
                c.save()

        return {
            'details': '\n'.join(['Business Area: {} - {}, Old Long Name: {}, New Name: {}'.format(*c)
                                  for c in countries_updated]),
            'total_records': len(records),  # len(records),
            'processed': len(list(countries_updated))
        }

    def _filter_records(self, records):
        local_business_area_codes = self.countries_qs.values_list('business_area_codes', flat=True)

        records = super()._filter_records(records)

        def bad_record(record):
            if not record['BUSINESS_AREA_CODE'] in local_business_area_codes:
                return False
            return True

        return [rec for rec in records if bad_record(rec)]
