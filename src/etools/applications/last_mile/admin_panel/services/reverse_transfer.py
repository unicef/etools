from django.db import transaction
from django.utils import timezone

from etools.applications.last_mile.admin_panel.validators import AdminPanelValidator
from etools.applications.last_mile.models import Item, Transfer


class TransferReverse:

    def __init__(self, transfer_id):
        self.transfer = Transfer.objects.filter(id=transfer_id).first()
        self.adminValidator = AdminPanelValidator()

    @transaction.atomic
    def _create_new_transfer(self, old_transfer):
        new_transfer_name = f"{old_transfer.partner_organization.name}_reversal_{timezone.now().strftime('%d-%m-%Y %H:%M:%S')}"
        new_status = Transfer.PENDING
        new_type = Transfer.DELIVERY
        new_partner_organization = old_transfer.partner_organization
        if old_transfer.transfer_type == Transfer.HANDOVER:
            new_partner_organization = old_transfer.from_partner_organization
        new_transfer = Transfer.objects.create(
            transfer_type=new_type,
            name=new_transfer_name,
            dispense_type=old_transfer.dispense_type,
            transfer_subtype=old_transfer.transfer_subtype,
            status=new_status,
            origin_point=old_transfer.destination_point,
            destination_point=old_transfer.origin_point,
            partner_organization=new_partner_organization,
            unicef_release_order=old_transfer.unicef_release_order,
            origin_transfer=old_transfer,
            reason=old_transfer.reason,
            comment=old_transfer.comment,
            transfer_history=old_transfer.transfer_history,
            purchase_order_id=old_transfer.purchase_order_id,
            waybill_id=old_transfer.waybill_id,
            pd_number=old_transfer.pd_number,
            initial_items=old_transfer.initial_items
        )
        Item.all_objects.filter(transfer=old_transfer).update(transfer=new_transfer)
        return new_transfer

    def reverse(self):
        old_transfer = self.transfer
        self.adminValidator.validate_reverse_transfer(old_transfer)
        self.adminValidator.validate_transfer_items(old_transfer)
        new_transfer = self._create_new_transfer(old_transfer)
        return new_transfer
