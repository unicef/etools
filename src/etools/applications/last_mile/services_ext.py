from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

from django.db.models import F, FloatField, Func, QuerySet

from etools.applications.last_mile import models


@dataclass
class IngestResultDTO:
    created_count: int
    skipped_existing_in_db: List[str]
    skipped_duplicate_in_payload: List[str]


class MaterialIngestService:

    def ingest_materials(self, validated_data: List[Dict[str, Any]]) -> IngestResultDTO:
        incoming_numbers = {item['number'] for item in validated_data}

        existing_numbers = set(
            models.Material.objects.filter(number__in=incoming_numbers).values_list('number', flat=True)
        )
        materials_to_create = []
        processed_numbers = set()
        skipped_due_to_db_duplicate = []
        skipped_due_to_payload_duplicate = []

        for material_data in validated_data:
            number = material_data['number']

            if number in existing_numbers:
                skipped_due_to_db_duplicate.append(number)
                continue

            if number in processed_numbers:
                skipped_due_to_payload_duplicate.append(number)
                continue

            materials_to_create.append(models.Material(**material_data))
            processed_numbers.add(number)

        if materials_to_create:
            models.Material.objects.bulk_create(materials_to_create)

        return IngestResultDTO(
            created_count=len(materials_to_create),
            skipped_existing_in_db=skipped_due_to_db_duplicate,
            skipped_duplicate_in_payload=skipped_due_to_payload_duplicate
        )


class GeometryPointFunc(Func):
    template = "%(function)s(%(expressions)s::geometry)"

    def __init__(self, expression):
        super().__init__(expression, output_field=FloatField())


class Latitude(GeometryPointFunc):
    function = 'ST_Y'


class Longitude(GeometryPointFunc):
    function = 'ST_X'


class ExportError(Exception):
    pass


class InvalidModelTypeError(ExportError):
    pass


class InvalidDateFormatError(ExportError, ValueError):
    pass


def _prepare_transfer_qs(qs: QuerySet) -> QuerySet:
    return qs.annotate(
        vendor_number=F('partner_organization__organization__vendor_number'),
        checked_out_by_email=F('checked_out_by__email'),
        checked_out_by_first_name=F('checked_out_by__first_name'),
        checked_out_by_last_name=F('checked_out_by__last_name'),
        checked_in_by_email=F('checked_in_by__email'),
        checked_in_by_last_name=F('checked_in_by__last_name'),
        checked_in_by_first_name=F('checked_in_by__first_name'),
        origin_name=F('origin_point__name'),
        destination_name=F('destination_point__name'),
    ).values()


def _prepare_poi_qs(qs: QuerySet) -> QuerySet:
    return qs.prefetch_related('parent', 'poi_type').annotate(
        latitude=Latitude('point'),
        longitude=Longitude('point'),
        parent_pcode=F('parent__p_code'),
        vendor_number=F('partner_organizations__organization__vendor_number'),
    ).values(
        'id', 'created', 'modified', 'parent_id', 'name', 'description', 'poi_type_id',
        'other', 'private', 'is_active', 'latitude', 'longitude', 'parent_pcode',
        'p_code', 'vendor_number'
    )


def _prepare_item_qs(qs: QuerySet) -> QuerySet:
    return qs.annotate(
        material_number=F('material__number'),
        material_description=F('material__short_description'),
    ).values()


def _prepare_default_qs(qs: QuerySet) -> QuerySet:
    return qs.values()


class DataExportService:

    MODEL_CONFIG = {
        "transfer": (models.Transfer.objects, _prepare_transfer_qs),
        "poi": (models.PointOfInterest.all_objects, _prepare_poi_qs),
        "item": (models.Item.objects, _prepare_item_qs),
        "item_history": (models.ItemTransferHistory.objects, _prepare_default_qs),
        "poi_type": (models.PointOfInterestType.objects, _prepare_default_qs),
    }

    def get_export_queryset(self, model_type: str, last_modified: str = None) -> QuerySet:
        if model_type not in self.MODEL_CONFIG:
            raise InvalidModelTypeError(f"'{model_type}' is not a valid data model type.")

        manager, preparer_func = self.MODEL_CONFIG[model_type]
        queryset = manager.all()

        if last_modified:
            try:
                gte_dt = datetime.fromisoformat(last_modified)
                queryset = queryset.filter(modified__gte=gte_dt)
            except ValueError:
                raise InvalidDateFormatError("Invalid ISO 8601 format for 'last_modified'.")

        return preparer_func(queryset)
