from django.utils import timezone

from etools.applications.last_mile import models
from etools.applications.last_mile.admin_panel.constants import TRANSFER_MANUAL_CREATION_NAME


class StockManagementCreateService:

    def create_stock_management(self, validated_data):
        """
        validated_data should contain a dict with the following keys:
            - items (list), each item is a dict with the following keys:
                - material (models.Material),
                - quantity (int),
                - uom (str),
                - batch_id (str),
            - location (models.Location),
            - partner_organization (models.PartnerOrganization)
        """
        items = validated_data.pop('items', [])
        validated_data['unicef_release_order'] = f"{TRANSFER_MANUAL_CREATION_NAME} {timezone.now().strftime('%d-%m-%Y %H:%M:%S.%f')}"
        validated_data['transfer_type'] = models.Transfer.DELIVERY
        validated_data['status'] = models.Transfer.PENDING
        validated_data['approval_status'] = models.Transfer.ApprovalStatus.PENDING
        validated_data['origin_point'] = models.PointOfInterest.objects.get_unicef_warehouses()
        validated_data['destination_point'] = validated_data.pop('location')
        instance = models.Transfer.objects.create(
            **validated_data
        )
        items_to_create = []
        for item in items:
            items_to_create.append(
                models.Item(
                    transfer=instance,
                    material=item.get('material'),
                    quantity=item.get('quantity'),
                    uom=item.get('uom'),
                    batch_id=item.get('item_name'),
                    expiry_date=item.get('expiration_date') or item.get('expiry_date'),
                )
            )
        models.Item.objects.bulk_create(items_to_create)
        return instance
