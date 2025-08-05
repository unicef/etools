from django.db import transaction
from django.utils import timezone

from etools.applications.last_mile.admin_panel.validators import AdminPanelValidator
from etools.applications.last_mile.models import Item, Transfer


class ReverseTransfer:

    def __init__(self, transfer_id=None):
        self.transfer = Transfer.objects.filter(id=transfer_id).select_related("origin_point", "destination_point", "origin_point__poi_type", "destination_point__poi_type").first()
        self.adminValidator = AdminPanelValidator()

    def decide_origin_and_destination_location(self):
        final_origin_point = None
        final_destination_point = None
        origin_point = self.transfer.origin_point
        destination_point = self.transfer.destination_point
        if origin_point and origin_point.poi_type.category.lower() == 'warehouse':
            final_origin_point = origin_point
        elif destination_point and destination_point.poi_type.category.lower() == 'warehouse':
            final_origin_point = destination_point
        else:
            final_origin_point = destination_point
            final_destination_point = origin_point
        return final_origin_point, final_destination_point

    @transaction.atomic
    def _create_new_transfer(self):
        new_transfer_name = f"{self.transfer.partner_organization.name}_reversal_{timezone.now().strftime('%d-%m-%Y %H:%M:%S')}"
        new_status = Transfer.PENDING
        new_type = Transfer.DELIVERY
        new_partner_organization = self.transfer.partner_organization
        reversed_unicef_release_order = f"{self.transfer.unicef_release_order}_reversed"
        origin_point, destination_point = self.decide_origin_and_destination_location()
        new_transfer = Transfer.objects.create(
            transfer_type=new_type,
            name=new_transfer_name,
            status=new_status,
            origin_point=origin_point,
            destination_point=destination_point,
            partner_organization=new_partner_organization,
            unicef_release_order=reversed_unicef_release_order[:254],  # To not overload the max_length of the field
            origin_transfer=self.transfer,
            reason=self.transfer.reason,
            comment=self.transfer.comment,
            transfer_history=self.transfer.transfer_history,
            purchase_order_id=self.transfer.purchase_order_id,
            waybill_id=self.transfer.waybill_id,
            pd_number=self.transfer.pd_number,
            initial_items=self.transfer.initial_items
        )
        Item.all_objects.filter(transfer=self.transfer).update(transfer=new_transfer)
        return new_transfer

    def reverse(self):
        old_transfer = self.transfer
        self.adminValidator.validate_reverse_transfer(old_transfer)
        self.adminValidator.validate_transfer_items(old_transfer)
        self.adminValidator.validate_transfer_type(old_transfer)
        new_transfer = self._create_new_transfer()
        return new_transfer
