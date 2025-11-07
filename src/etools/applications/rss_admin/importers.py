from django.contrib.gis.geos import Point

import openpyxl

from etools.applications.field_monitoring.fm_settings.models import LocationSite
from etools.applications.utils.helpers import generate_hash


class LocationSiteImporter:
    required_headers = ['Site_Name', 'Latitude', 'Longitude']

    @staticmethod
    def _get_pcode(split_name, name):
        p_code = split_name[1].strip() if len(split_name) > 1 else None
        if not p_code or p_code == "None":
            return generate_hash(name, 12)
        return p_code

    def import_file(self, upload):
        try:
            wb = openpyxl.load_workbook(upload)
        except Exception:  # noqa
            return False, {'detail': 'Invalid or unreadable XLSX file'}

        sheet = wb.active
        headers = [cell.value for cell in sheet[1]]
        if any(h not in headers for h in self.required_headers):
            return False, {'detail': 'Missing required columns: Site_Name, Latitude, Longitude'}

        header_idx = {h: headers.index(h) for h in headers}

        created = 0
        updated = 0
        skipped = 0

        for row_idx in range(2, sheet.max_row + 1):
            row = [c.value for c in sheet[row_idx]]
            name_raw = row[header_idx['Site_Name']]
            if not name_raw or str(name_raw).strip() == 'None':
                skipped += 1
                continue

            try:
                split_name = str(name_raw).split('_')
                clean_name = split_name[0].split(':')[1].strip()
            except Exception:  # noqa
                skipped += 1
                continue

            p_code = self._get_pcode(split_name, clean_name)
            try:
                longitude = float(str(row[header_idx['Longitude']]).strip())
                latitude = float(str(row[header_idx['Latitude']]).strip())
            except Exception:  # noqa
                skipped += 1
                continue

            point = Point(longitude, latitude)
            obj, was_created = LocationSite.objects.update_or_create(
                p_code=p_code,
                defaults={
                    'point': point,
                    'name': clean_name,
                }
            )
            if was_created:
                created += 1
            else:
                updated += 1

        return True, {'created': created, 'updated': updated, 'skipped': skipped}


