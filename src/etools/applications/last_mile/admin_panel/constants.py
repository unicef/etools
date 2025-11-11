ADMIN_PANEL_APP_NAME = 'last_mile_admin'

ALERT_TYPES = {
    "LMSM Focal Point": "Wastage Notification",
    "LMSM Alert Receipt": "Acknowledgement by IP",
    "Waybill Recipient": "Waybill Recipient",
    "LMSM User Creation Report": "LMSM User Creation Report",
    "LMSM Dispensing Notification": "Dispensing Notification"
}

TRANSFER_MANUAL_CREATION_NAME = "INITIAL STOCK UPLOAD @"

USER_ADMIN_PANEL = 'users-admin-panel'
UPDATE_USER_PROFILE_ADMIN_PANEL = 'update-user-profile-admin-panel'
USER_LOCATIONS_ADMIN_PANEL = 'user-location-admin-panel'
USER_ADMIN_PANEL_PERMISSION = 'lmsm_admin_panel_manage_users'

LOCATIONS_ADMIN_PANEL = 'locations-admin-panel'
LOCATIONS_TYPE_ADMIN_PANEL = 'location-type-admin-panel'
PARENT_LOCATIONS_ADMIN_PANEL = 'parent-locations'
PARTNER_ORGANIZATIONS_ADMIN_PANEL = 'partner-organizations-admin'
POINT_OF_INTERESTS_LIGHT_DATA = 'point-of-interests-light-data'
GEOPOINT_LOCATIONS = 'geopoint-locations'
LOCATIONS_ADMIN_PANEL_PERMISSION = 'lmsm_admin_panel_manage_locations'
LOCATIONS_BULK_REVIEW_ADMIN_PANEL = 'locations-bulk-review'

ALERT_NOTIFICATIONS_ADMIN_PANEL = 'alert-notification'
ALERT_TYPES_ADMIN_PANEL = 'alert-type'
ALERT_NOTIFICATIONS_ADMIN_PANEL_PERMISSION = 'lmsm_admin_panel_manage_email_alerts'

STOCK_MANAGEMENT_ADMIN_PANEL = 'stock-management'
STOCK_MANAGEMENT_MATERIALS_ADMIN_PANEL = 'materials-admin-panel'
UPDATE_ITEM_STOCK_ADMIN_PANEL = 'update-item-stock-admin-panel'
STOCK_MANAGEMENT_ADMIN_PANEL_PERMISSION = 'lmsm_admin_panel_manage_stock_management'

TRANSFER_HISTORY_ADMIN_PANEL = 'transfer-history'
TRANSFER_EVIDENCE_ADMIN_PANEL = 'transfer-evidence'
TRANSFER_REVERSE_ADMIN_PANEL = 'transfer-items-reverse'
TRANSFER_HISTORY_ADMIN_PANEL_PERMISSION = 'lmsm_admin_panel_manage_transfer_history'
TRANSFER_BULK_REVIEW_ADMIN_PANEL = 'transfer-bulk-review'

APPROVE_USERS_ADMIN_PANEL_PERMISSION = 'lmsm_admin_panel_approve_users'
APPROVE_LOCATIONS_ADMIN_PANEL_PERMISSION = 'lmsm_admin_panel_approve_locations'
APPROVE_STOCK_MANAGEMENT_ADMIN_PANEL_PERMISSION = 'lmsm_admin_panel_approve_stock_management'

# Error messages
POI_TYPE_ALREADY_EXISTS = "poi_type_already_exists"
USER_DOES_NOT_EXIST = "user_does_not_exist"
GROUP_NOT_AVAILABLE = "group_not_available"
GROUP_DOES_NOT_EXIST = "group_does_not_exist"
USER_NOT_PROVIDED = "user_not_provided"
GROUP_NOT_PROVIDED = "group_not_provided"
EMAIL_NOT_PROVIDED = "email_not_provided"
REALM_ALREADY_EXISTS = "realm_already_exists"
ORGANIZATION_DOES_NOT_EXIST = "organization_does_not_exist"
PARTNER_NOT_UNDER_ORGANIZATION = "partner_not_under_organization"
ITEMS_NOT_PROVIDED = "items_not_provided"
ONLY_ONE_ITEM_PER_TRANSFER = "only_one_item_per_transfer"
INVALID_QUANTITY = "invalid_quantity"
UOM_NOT_PROVIDED = "uom_not_provided"
UOM_NOT_VALID = "uom_not_valid"
PARTNER_NOT_UNDER_LOCATION = "partner_not_under_location"
LAST_MILE_PROFILE_NOT_FOUND = "last_mile_profile_not_found"
STATUS_NOT_CORRECT = "status_not_correct"
TRANSFER_NOT_FOUND_FOR_REVERSE = "transfer_not_found_for_reverse"
TRANSFER_HAS_NO_ITEMS = "transfer_has_no_items"
TRANSFER_TYPE_HANDOVER_NOT_ALLOWED = "transfer_type_handover_not_allowed"
BATCH_ID_TOO_LONG = "batch_id_too_long"
INVALID_EXPIRATION_DATE = "invalid_expiration_date"
INVALID_ORGANIZATION_ID = "invalid_organization_id"
USER_CANT_APPROVE = "user_cant_approve"

LIST_INTERESTED_LASTMILE_PERMS = [
    USER_ADMIN_PANEL_PERMISSION,
    LOCATIONS_ADMIN_PANEL_PERMISSION,
    APPROVE_USERS_ADMIN_PANEL_PERMISSION,
    STOCK_MANAGEMENT_ADMIN_PANEL_PERMISSION,
    TRANSFER_HISTORY_ADMIN_PANEL_PERMISSION,
    APPROVE_LOCATIONS_ADMIN_PANEL_PERMISSION,
    ALERT_NOTIFICATIONS_ADMIN_PANEL_PERMISSION,
    APPROVE_STOCK_MANAGEMENT_ADMIN_PANEL_PERMISSION,
]
