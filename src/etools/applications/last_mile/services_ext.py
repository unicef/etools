from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List

from django.db import connection
from django.db.models import QuerySet, Value

from etools.applications.last_mile import models
from etools.applications.last_mile.validator_ext import ItemValidator, ValidatorEXT


@dataclass
class IngestResultDTO:
    created_count: int
    skipped_existing_in_db: List[str]
    skipped_duplicate_in_payload: List[str]


class MaterialIngestService:

    CUSTOM_UOM_OVERRIDES = {
        "S0000237": {
            "original_uom": "CAR",
            "other": {"uom_map": {"CAN": 1, "CAR": 24}}
        },
        "S0000236": {
            "original_uom": "CAR",
            "other": {"uom_map": {"CAN": 1, "CAR": 24}}
        }
    }

    def _check_and_update_custom_uom(self, existing_materials: List[models.Material]) -> int:
        updated_count = 0

        for material in existing_materials:
            if material.number in self.CUSTOM_UOM_OVERRIDES:
                override = self.CUSTOM_UOM_OVERRIDES[material.number]
                needs_update = False

                if material.original_uom != override["original_uom"]:
                    needs_update = True

                current_uom_map = material.other.get("uom_map", {}) if material.other else {}
                override_uom_map = override["other"].get("uom_map", {})

                if current_uom_map != override_uom_map:
                    needs_update = True

                if needs_update:
                    material.original_uom = override["original_uom"]
                    if material.other is None:
                        material.other = {}
                    material.other.update(override["other"])
                    material.save()
                    updated_count += 1

        return updated_count

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

        overwrite_materials = models.Material.objects.filter(number__in=self.CUSTOM_UOM_OVERRIDES.keys())

        self._check_and_update_custom_uom(overwrite_materials)

        return IngestResultDTO(
            created_count=len(materials_to_create),
            skipped_existing_in_db=skipped_due_to_db_duplicate,
            skipped_duplicate_in_payload=skipped_due_to_payload_duplicate
        )


class ExportError(Exception):
    pass


class InvalidModelTypeError(ExportError):
    pass


class InvalidDateFormatError(ExportError, ValueError):
    pass


class DataExportService:

    MODEL_CONFIG = {
        "transfer": models.Transfer.objects,
        "poi": models.PointOfInterest.export_objects,
        "item": models.Item.objects,
        "item_history": models.ItemTransferHistory.objects,
        "poi_type": models.PointOfInterestType.objects,
        "item_audit_log": models.ItemAuditLog.objects
    }

    def get_export_queryset(self, model_type: str, last_modified: str = None) -> QuerySet:
        if model_type not in self.MODEL_CONFIG:
            raise InvalidModelTypeError(f"'{model_type}' is not a valid data model type.")

        manager = self.MODEL_CONFIG[model_type]
        queryset = manager.all()

        if last_modified:
            try:
                gte_dt = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
                queryset = queryset.filter(modified__gte=gte_dt)
            except (ValueError, TypeError):
                raise InvalidDateFormatError("Invalid ISO 8601 format for 'last_modified'.")

        country_name = connection.tenant.name if hasattr(connection, 'tenant') else None
        country_code = connection.tenant.country_short_code if hasattr(connection, 'tenant') else None
        queryset = queryset.prepare_for_lm_export()

        if country_name:
            queryset = queryset.annotate(country=Value(country_name), country_code=Value(country_code))

        queryset = queryset.order_by('id')
        return queryset


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
        self.validator_ext = ValidatorEXT()

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
                organization = self.validator_ext.validate_organization(vendor_number)
                transfer_data['partner_organization'] = organization.partner
            except ValueError as e:
                self.report.skipped_transfers.append({"release_order": release_order, "reason": str(e)})
                continue

            origin_poi = models.PointOfInterest.objects.get_unicef_warehouses()

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

    def _build_item_instance(
        self,
        validated_data: dict,
        material: models.Material,
        transfer: models.Transfer
    ) -> models.Item:

        other_data = {
            'HandoverNumber': validated_data.get('other', {}).get('HandoverNumber'),
            'HandoverItem': validated_data.get('other', {}).get('HandoverItem'),
            'HandoverYear': validated_data.get('other', {}).get('HandoverYear'),
            'Plant': validated_data.get('other', {}).get('Plant'),
            'PurchaseOrderType': validated_data.get('other', {}).get('PurchaseOrderType'),
            'itemid': validated_data.get('other', {}).get('itemid'),
        }

        return models.Item(
            material=material,
            transfer=transfer,
            unicef_ro_item=validated_data.get('unicef_ro_item'),
            quantity=validated_data.get('quantity'),
            batch_id=validated_data.get('batch_id'),
            expiry_date=validated_data.get('expiry_date'),
            purchase_order_item=validated_data.get('purchase_order_item'),
            amount_usd=validated_data.get('amount_usd'),
            uom=validated_data.get('uom'),
            conversion_factor=validated_data.get('conversion_factor'),
            base_quantity=validated_data.get('quantity'),
            base_uom=validated_data.get('uom') if validated_data.get('uom') else material.original_uom,
            other=other_data
        )

    def _prepare_items(self) -> List[models.Item]:
        items_to_create = []
        all_transfers = {t.unicef_release_order: t for t in models.Transfer.objects.filter(unicef_release_order__in=self.items_by_release_order.keys())}
        all_material_numbers = {item['material_number'] for items in self.items_by_release_order.values() for item in items}
        all_materials = {m.number: m for m in models.Material.objects.filter(number__in=all_material_numbers)}

        all_incoming_item_ids = {
            item.get('other', {}).get('itemid')
            for items in self.items_by_release_order.values()
            for item in items
            if item.get('other', {}).get('itemid')
        }

        existing_item_ids_in_db = set(
            models.Item.objects.filter(other__itemid__in=all_incoming_item_ids).values_list('other__itemid', flat=True)
        )

        processed_item_ids_in_this_run = set()
        itemValidator = ItemValidator(all_materials, existing_item_ids_in_db)
        for release_order, items in self.items_by_release_order.items():
            transfer = all_transfers.get(release_order)
            if not transfer:
                self.report.skipped_items.extend([{"item": item, "reason": f"Parent transfer {release_order} not found or created."} for item in items])
                continue

            for item_data in items:
                material, reason = itemValidator.validate(item_data, processed_item_ids_in_this_run)

                if reason:
                    self.report.skipped_items.append({"item": item_data, "reason": reason})
                    continue

                item_id = item_data.get('other', {}).get('itemid')

                if item_data.get('uom') == material.original_uom:
                    item_data.pop('uom', None)

                if item_data.get('uom') == "EA":
                    item_data['conversion_factor'] = 1.0

                if not item_data.get('batch_id'):
                    item_data['conversion_factor'] = 1.0
                    item_data['uom'] = "EA"

                item = self._build_item_instance(item_data, material, transfer)
                items_to_create.append(item)

                if item_id:
                    processed_item_ids_in_this_run.add(item_id)

        return items_to_create
