import csv
from io import StringIO
from typing import Any, Dict, Iterator, List


class BaseCSVExporter:

    DEFAULT_CHUNK_SIZE = 1000

    def __init__(self, chunk_size: int = DEFAULT_CHUNK_SIZE):
        self.chunk_size = chunk_size

    def _write_csv_rows_bulk(self, rows_data: List[List[Any]]) -> str:
        output = StringIO()
        writer = csv.writer(output)
        writer.writerows(rows_data)
        output.seek(0)
        return output.read()

    def _write_csv_row(self, row_data: List[Any]) -> str:
        return self._write_csv_rows_bulk([row_data])

    def _serialize_items_batch(self, items: List[Any], serializer_class: Any) -> List[Dict[str, Any]]:
        return serializer_class(items, many=True).data

    def _extract_values_bulk(self, data_list: List[Dict[str, Any]], headers: List[str]) -> List[List[Any]]:
        return [[data.get(header, '') for header in headers] for data in data_list]

    def _process_chunk_with_batch_serialization(
        self, chunk: List[Any], serializer_class: Any, headers: Dict[str, str]
    ) -> Iterator[str]:
        serialized_data_list = self._serialize_items_batch(chunk, serializer_class)
        rows_values = self._extract_values_bulk(serialized_data_list, list(headers.keys()))
        if rows_values:
            yield self._write_csv_rows_bulk(rows_values)

    def _process_chunk_with_row_expansion(
        self, chunk: List[Any], serializer_class: Any, headers: Dict[str, str]
    ) -> Iterator[str]:
        all_rows = []

        if hasattr(serializer_class, 'bulk_generate_rows'):
            all_rows = serializer_class.bulk_generate_rows(chunk)
        else:
            for obj in chunk:
                item_serializer = serializer_class(obj)
                rows = item_serializer.generate_rows(obj)
                all_rows.extend(rows)

        if all_rows:
            rows_values = self._extract_values_bulk(all_rows, list(headers.keys()))
            yield self._write_csv_rows_bulk(rows_values)

    def _paginate_queryset(self, queryset) -> Iterator[list]:
        """Paginate queryset in chunks, preserving prefetch_related.

        Unlike .iterator(), this evaluates each chunk as a separate
        queryset slice so prefetch_related lookups are properly applied.
        """
        offset = 0
        while True:
            chunk = list(queryset[offset:offset + self.chunk_size])
            if not chunk:
                break
            yield chunk
            offset += self.chunk_size

    def _iterate_with_chunking(
        self, queryset, serializer_class: Any, headers: Dict[str, str], use_row_expansion: bool = False
    ) -> Iterator[str]:
        process_method = (
            self._process_chunk_with_row_expansion if use_row_expansion
            else self._process_chunk_with_batch_serialization
        )

        for chunk in self._paginate_queryset(queryset):
            yield from process_method(chunk, serializer_class, headers)


class UsersCSVExporter(BaseCSVExporter):

    def generate_csv_data(self, queryset, serializer_class) -> Iterator[str]:
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
        yield from self._iterate_with_chunking(queryset, serializer_class, headers)


class LocationsCSVExporter(BaseCSVExporter):

    def generate_csv_data(self, queryset, serializer_class, only_locations=False) -> Iterator[str]:
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
            "implementing_partner_names": "Implementing Partner Name",
            "implementing_partner_numbers": "Implementing Partner Number",
            "region": "Region",
            "district": "District",
            "country": "Country",
            "transfer_name": "Transfer Name",
            "transfer_ref": "Transfer Reference",
            "item_id": "Item ID",
            "item_name": "Item Name",
            "item_qty": "Item Quantity",
            "item_batch_number": "Item Batch Number",
            "item_expiry_date": "Item Expiry Date",
            "approval_status": "Approval Status",
        }

        queryset = self._optimize_queryset(queryset)

        if not queryset.exists():
            return

        if only_locations:
            yield self._write_csv_row(standard_headers.values())
            for chunk in self._chunk_queryset(queryset):
                rows_data = []
                for location in chunk:
                    serialized = serializer_class(location).data
                    row_values = [serialized.get(header, '') for header in standard_headers.keys()]
                    rows_data.append(row_values)
                if rows_data:
                    yield self._write_csv_rows_bulk(rows_data)
        else:
            has_row_expansion = hasattr(serializer_class, 'generate_rows')
            if has_row_expansion:
                yield self._write_csv_row(expanded_headers.values())
                self.chunk_size = min(self.chunk_size, 500)  # Limit to avoid memory issues
                yield from self._iterate_with_chunking(
                    queryset, serializer_class, expanded_headers, use_row_expansion=True
                )
            else:
                yield self._write_csv_row(standard_headers.values())
                yield from self._iterate_with_chunking(queryset, serializer_class, standard_headers)

    def _chunk_queryset(self, queryset):
        yield from self._paginate_queryset(queryset)

    def _optimize_queryset(self, queryset):
        queryset = queryset.distinct()

        if not hasattr(queryset, '_prefetch_related_lookups') or not queryset._prefetch_related_lookups:
            queryset = queryset.prefetch_related(
                'partner_organizations__organization',
                'poi_type',
                'parent'
            )
        return queryset


class UserLocationsCSVExporter(BaseCSVExporter):

    def generate_csv_data(self, queryset, serializer_class) -> Iterator[str]:
        headers = {
            "id": "Unique ID",
            "first_name": "First Name",
            "last_name": "Last Name",
            "email": "Email",
            "implementing_partner": "Implementing Partner",
            "location": "Location"
        }

        yield self._write_csv_row(headers.values())
        yield from self._iterate_with_chunking(queryset, serializer_class, headers)


class POITypesCSVExporter(BaseCSVExporter):

    def generate_csv_data(self, queryset, serializer_class) -> Iterator[str]:
        headers = {
            "id": "Unique ID",
            "created": "Created",
            "modified": "Modified",
            "name": "Name",
            "category": "Category"
        }

        yield self._write_csv_row(headers.values())

        yield from self._iterate_with_chunking(queryset, serializer_class, headers)


class UserAlertNotificationsCSVExporter(BaseCSVExporter):

    def generate_csv_data(self, queryset, serializer_class) -> Iterator[str]:
        headers = {
            "email": "Email",
            "alert_types": "Alert Types"
        }
        yield self._write_csv_row(headers.values())

        yield from self._iterate_with_chunking(queryset, serializer_class, headers)
