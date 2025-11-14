from django.db import transaction

from etools.applications.last_mile import models


class TransferApprovalService:

    @transaction.atomic
    def bulk_review(self, items, approval_status, approver_user, review_notes=None):
        transfers_dict = {}
        for item in items:
            if item.transfer_id not in transfers_dict:
                transfers_dict[item.transfer_id] = {
                    'transfer': item.transfer,
                    'selected_items': [],
                    'all_items': list(item.transfer.items.all())
                }
            transfers_dict[item.transfer_id]['selected_items'].append(item.id)

        all_items_to_hide = set()
        all_items_to_show = set()
        transfers_to_update = []

        for _, data in transfers_dict.items():
            transfer = data['transfer']
            selected_item_ids = set(data['selected_items'])
            all_item_ids = {item.id for item in data['all_items']}

            items_to_hide = all_item_ids - selected_item_ids
            if items_to_hide:
                all_items_to_hide.update(items_to_hide)

            if approval_status == models.Transfer.ApprovalStatus.REJECTED:
                transfer.reject(approver_user, review_notes)
                all_items_to_hide.update(all_item_ids)
                transfers_to_update.append(transfer)
            elif approval_status == models.Transfer.ApprovalStatus.APPROVED:
                transfer.approve(approver_user, review_notes)
                all_items_to_show.update(selected_item_ids)
                transfers_to_update.append(transfer)

        if all_items_to_hide:
            models.Item.all_objects.filter(id__in=all_items_to_hide).update(hidden=True)
        if all_items_to_show:
            models.Item.all_objects.filter(id__in=all_items_to_show).update(hidden=False)

        if transfers_to_update:
            models.Transfer.all_objects.bulk_update(
                transfers_to_update,
                fields=['approval_status', 'approved_by', 'approved_on', 'review_notes'],
                batch_size=250
            )
        return True
