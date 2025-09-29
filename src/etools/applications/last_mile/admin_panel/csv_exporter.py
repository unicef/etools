import csv
from io import StringIO
from typing import Any, Dict, Iterator, List


class CsvExporter:

    DEFAULT_CHUNK_SIZE = 50

    def __init__(self, chunk_size: int = DEFAULT_CHUNK_SIZE):
        self.chunk_size = chunk_size

    def _write_csv_row(self, row_data: List[Any]) -> str:
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(row_data)
        output.seek(0)
        return output.read()

    def _serialize_item(self, item: Any, serializer_class: Any) -> Dict[str, Any]:
        return serializer_class(item).data

    def _get_first_item(self, queryset):
        for item in queryset[:1]:
            return item
        return None

    def _extract_values_from_dict(self, data: Dict[str, Any], headers: List[str]) -> List[Any]:
        return [data.get(header, '') for header in headers]

    def generate_csv_data_for_users(self, queryset, serializer_class) -> Iterator[str]:
        headers = {
            "first_name": "First Name",
            "last_name": "Last Name",
            "email": "Email",
            "implementing_partner": "Implementing Partner",
            "country": "Country",
            "is_active": "Active",
            "last_login": "Last Login",
            "status": "Status"
        }

        yield self._write_csv_row(headers.values())

        for user in queryset.iterator(chunk_size=self.chunk_size):
            serialized_data = self._serialize_item(user, serializer_class)
            row_values = self._extract_values_from_dict(serialized_data, headers.keys())
            yield self._write_csv_row(row_values)

    def generate_csv_data_for_locations(self, queryset, serializer_class, only_locations) -> Iterator[str]:
        standard_headers = {
            "id": "Unique ID",
            "name": "Name",
            "primary_type": "Primary Type",
            "p_code": "P Code",
            "lat": "Latitude",
            "lng": "Longitude",
            "status": "Status",
            "implementing_partner": "Implementing Partner",
            "region": "Region",
            "district": "District",
            "country": "Country"
        }

        expanded_headers = {
            "id": "Unique ID",
            "name": "Name",
            "primary_type": "Primary Type",
            "p_code": "P Code",
            "lat": "Latitude",
            "lng": "Longitude",
            "status": "Status",
            "implementing_partner": "Implementing Partner",
            "region": "Region",
            "district": "District",
            "country": "Country",
            "transfer_name": "Transfer Name",
            "transfer_ref": "Transfer Reference",
            "item_id": "Item ID",
            "item_name": "Item Name",
            "item_qty": "Item Quantity"
        }

        first_item = self._get_first_item(queryset)
        if not first_item:
            return

        serializer = serializer_class(first_item)
        has_row_expansion = hasattr(serializer, 'generate_rows')

        if only_locations and has_row_expansion:
            has_row_expansion = False

        if has_row_expansion:
            yield self._write_csv_row(expanded_headers.values())

            first_rows = serializer.generate_rows(first_item)
            for row_data in first_rows:
                row_values = self._extract_values_from_dict(row_data, expanded_headers.keys())
                yield self._write_csv_row(row_values)

            for item in queryset[1:].iterator(chunk_size=self.chunk_size):
                item_serializer = serializer_class(item)
                rows = item_serializer.generate_rows(item)
                for row_data in rows:
                    row_values = self._extract_values_from_dict(row_data, expanded_headers.keys())
                    yield self._write_csv_row(row_values)
        else:
            yield self._write_csv_row(standard_headers.values())

            for item in queryset.iterator(chunk_size=self.chunk_size):
                serialized_data = self._serialize_item(item, serializer_class)
                row_values = self._extract_values_from_dict(serialized_data, standard_headers.keys())
                yield self._write_csv_row(row_values)

    def generate_csv_data_for_user_locations(self, queryset, serializer_class) -> Iterator[str]:
        headers = {
            "id": "Unique ID",
            "first_name": "First Name",
            "last_name": "Last Name",
            "email": "Email",
            "implementing_partner": "Implementing Partner",
            "location": "Location"
        }

        yield self._write_csv_row(headers.values())

        for user in queryset.iterator(chunk_size=self.chunk_size):
            serialized_data = self._serialize_item(user, serializer_class)
            row_values = self._extract_values_from_dict(serialized_data, headers.keys())
            yield self._write_csv_row(row_values)

    def generate_csv_data_for_poi_types(self, queryset, serializer_class) -> Iterator[str]:
        headers = {
            "id": "Unique ID",
            "created": "Created",
            "modified": "Modified",
            "name": "Name",
            "category": "Category"
        }

        yield self._write_csv_row(headers.values())

        for poi_type in queryset.iterator(chunk_size=self.chunk_size):
            serialized_data = self._serialize_item(poi_type, serializer_class)
            row_values = self._extract_values_from_dict(serialized_data, headers.keys())
            yield self._write_csv_row(row_values)
