ITEM_AUDIT_LOG_ENABLED = True

ITEM_AUDIT_LOG_TRACKED_FIELDS = [
    'quantity',
    'uom',
    'conversion_factor',
    'wastage_type',
    'batch_id',
    'expiry_date',
    'comment',
    'mapped_description',
    'hidden',
    'transfer_id',
    'material_id',
    'is_prepositioned',
    'preposition_qty',
    'amount_usd',
    'base_quantity',
    'base_uom'
]

ITEM_AUDIT_LOG_EXCLUDE_USERS = []

ITEM_AUDIT_LOG_MAX_ENTRIES_PER_ITEM = 100


ITEM_AUDIT_LOG_SYSTEM_USERS = True

ITEM_AUDIT_LOG_FK_FIELDS = {
    'transfer_id': 'transfer',
    'material_id': 'material'
}
