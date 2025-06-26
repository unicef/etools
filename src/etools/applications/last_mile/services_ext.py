from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List

from django.db.models import F, FloatField, Func, QuerySet

from etools.applications.last_mile import models
from etools.applications.organizations.models import Organization


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


@dataclass
class IngestReportDTO:
    transfers_created: int = 0
    items_created: int = 0
    skipped_transfers: List[Dict[str, Any]] = field(default_factory=list)
    skipped_items: List[Dict[str, Any]] = field(default_factory=list)


class TransferIngestService:
    def __init__(self):
        self.report = IngestReportDTO()
        self.transfers_to_create = []
        self.processed_release_orders = set()
        self.items_by_release_order = {}

    def ingest_validated_data(self, validated_data: List[Dict[str, Any]]) -> IngestReportDTO:
        self._prepare_transfers_and_group_items(validated_data)

        if self.transfers_to_create:
            created_transfers = models.Transfer.objects.bulk_create(self.transfers_to_create)
            self.report.transfers_created = len(created_transfers)

        items_to_create = self._prepare_items()
        if items_to_create:
            created_items = models.Item.objects.bulk_create(items_to_create)
            self.report.items_created = len(created_items)

        return self.report

    def _prepare_transfers_and_group_items(self, validated_data: List[Dict[str, Any]]):
        for row in validated_data:
            transfer_data = row['transfer_data']
            item_data = row['item_data']
            release_order = transfer_data.get('unicef_release_order')

            vendor_number = transfer_data.pop('vendor_number')
            try:
                organization = Organization.objects.select_related('partner').get(vendor_number=vendor_number)
                if not hasattr(organization, 'partner'):
                    raise ValueError(f"No partner available for vendor {vendor_number}")
                transfer_data['partner_organization'] = organization.partner
            except (Organization.DoesNotExist, ValueError) as e:
                self.report.skipped_transfers.append({"release_order": release_order, "reason": str(e)})
                continue
            try:
                origin_poi = models.PointOfInterest.objects.get_unicef_warehouses()
            except models.PointOfInterest.DoesNotExist:
                self.report.skipped_transfers.append({"release_order": release_order, "reason": "No Unicef Warehouse Defined"})
                continue

            if release_order not in self.processed_release_orders:
                try:
                    models.Transfer.objects.get(unicef_release_order=release_order)
                except models.Transfer.DoesNotExist:
                    transfer_data.update({
                        'transfer_type': models.Transfer.DELIVERY,
                        'origin_point': origin_poi,  # Unicef Warehouse
                    })
                    self.transfers_to_create.append(models.Transfer(**transfer_data))

                self.processed_release_orders.add(release_order)

            self.items_by_release_order.setdefault(release_order, []).append(item_data)

    def _prepare_items(self):
        items_to_create = []
        all_transfers = {t.unicef_release_order: t for t in models.Transfer.objects.filter(unicef_release_order__in=self.items_by_release_order.keys())}
        all_material_numbers = {item['material_number'] for items in self.items_by_release_order.values() for item in items}
        all_materials = {m.number: m for m in models.Material.objects.filter(number__in=all_material_numbers)}

        for release_order, items in self.items_by_release_order.items():
            transfer = all_transfers.get(release_order)
            if not transfer:
                self.report.skipped_items.extend([{"item": item, "reason": f"Parent transfer {release_order} not found or created."} for item in items])
                continue

            for item_data in items:
                material_number = item_data.get('material_number')
                material = all_materials.get(material_number)
                if not material:
                    self.report.skipped_items.append({"item": item_data, "reason": f"Material number '{material_number}' not found."})
                    continue

                item_id = item_data.get('other', {}).get('itemid')
                if models.Item.objects.filter(other__itemid=item_id).exists() or \
                   models.Item.objects.filter(transfer=transfer, unicef_ro_item=item_data.get('unicef_ro_item')).exists():
                    self.report.skipped_items.append({"item": item_data, "reason": "Duplicate item found in database."})
                    continue

                item_data.pop('material_number', None)
                item_data.pop('description', None)  # Maybe changed with mapped_description?
                if item_data.get('uom') == material.original_uom:
                    item_data.pop('uom', None)

                item_data.update({
                    'material': material,
                    'transfer': transfer,
                    'base_quantity': item_data.get('quantity'),
                })
                if not item_data.get('batch_id'):
                    item_data['conversion_factor'] = 1.0
                    item_data['uom'] = "EA"

                items_to_create.append(models.Item(**item_data))

        return items_to_create
