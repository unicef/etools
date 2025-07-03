import io
import json

from django.db import transaction

import openpyxl

from etools.applications.last_mile.admin_panel.serializers import LocationImportSerializer, UserImportSerializer


class CsvImporter:

    def import_users(self, file, country_schema, user):
        data = file.read()
        stream = io.BytesIO(data)
        wb = openpyxl.load_workbook(stream)
        ws = wb.active
        error_col = ws.max_column + 1
        ws.cell(row=1, column=error_col, value='Errors')
        index = 3
        valid = True
        with transaction.atomic():
            for row in ws.iter_rows(min_row=3, max_row=ws.max_row, values_only=True):
                status_message = ''

                ip_number, first_name, last_name, email, point_of_interests, *_ = row
                if point_of_interests:
                    try:
                        point_of_interests = json.loads(point_of_interests)
                    except ValueError:
                        status_message += "Invalid point of interest format"
                        valid = False

                data = {
                    'ip_number': ip_number,
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'point_of_interests': [] if not point_of_interests else point_of_interests,
                }
                serializer = UserImportSerializer(data=data)
                if not serializer.is_valid():
                    status_message += str(serializer.errors)
                    valid = False
                if valid:
                    created, object_data = serializer.create(serializer.validated_data, country_schema, user)
                    if not created:
                        status_message += object_data
                        valid = False
                if valid:
                    status_message = 'Success'
                ws.cell(row=index, column=error_col, value=status_message)
                index += 1

        out = io.BytesIO()
        wb.save(out)
        out.seek(0)
        return valid, out

    def import_locations(self, file, user):
        data = file.read()
        stream = io.BytesIO(data)
        wb = openpyxl.load_workbook(stream)
        ws = wb.active
        error_col = ws.max_column + 1
        ws.cell(row=1, column=error_col, value='Errors')
        index = 3
        valid = True
        with transaction.atomic():
            for row in ws.iter_rows(min_row=3, max_row=ws.max_row, values_only=True):
                status_message = ''

                ip_numbers, location_name, primary_type_name, latitude, longitude, p_code_location, *_ = row
                if ip_numbers:
                    try:
                        ip_numbers = json.loads(ip_numbers)
                    except ValueError:
                        status_message += "Invalid IP Numbers format"
                        valid = False

                data = {
                    'ip_numbers': [] if not ip_numbers else ip_numbers,
                    'location_name': location_name,
                    'primary_type_name': primary_type_name,
                    'latitude': latitude,
                    'longitude': longitude,
                    'p_code_location': p_code_location
                }
                serializer = LocationImportSerializer(data=data)
                if not serializer.is_valid():
                    status_message += str(serializer.errors)
                    valid = False
                if valid:
                    created, object_data = serializer.create(serializer.validated_data, user)
                    if not created:
                        status_message += object_data
                        valid = False
                if valid:
                    status_message = 'Success'
                ws.cell(row=index, column=error_col, value=status_message)
                index += 1

        out = io.BytesIO()
        wb.save(out)
        out.seek(0)
        return valid, out

    def import_stock(self, file):
        print(f"file : {file}")
        pass
