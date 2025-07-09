ADMIN_PANEL_APP_NAME = 'last_mile_admin'

ALERT_TYPES = {
    "LMSM Focal Point": "Wastage Notification",
    "LMSM Alert Receipt": "Acknowledgement by IP",
    "Waybill Recipient": "Waybill Recipient",
    "LMSM User Creation Report": "LMSM User Creation Report",
    "LMSM Dispensing Notification": "Dispensing Notification"
}

TRANSFER_MANUAL_CREATION_NAME = "MT @"

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

ALERT_NOTIFICATIONS_ADMIN_PANEL = 'alert-notification'
ALERT_TYPES_ADMIN_PANEL = 'alert-type'
ALERT_NOTIFICATIONS_ADMIN_PANEL_PERMISSION = 'lmsm_admin_panel_manage_email_alerts'

STOCK_MANAGEMENT_ADMIN_PANEL = 'stock-management'
STOCK_MANAGEMENT_MATERIALS_ADMIN_PANEL = 'materials-admin-panel'
STOCK_MANAGEMENT_ADMIN_PANEL_PERMISSION = 'lmsm_admin_panel_manage_stock_management'

TRANSFER_HISTORY_ADMIN_PANEL = 'transfer-history'
TRANSFER_EVIDENCE_ADMIN_PANEL = 'transfer-evidence'
TRANSFER_ITEMS_ADMIN_PANEL = 'transfer-items'
TRANSFER_HISTORY_ADMIN_PANEL_PERMISSION = 'lmsm_admin_panel_manage_transfer_history'

APPROVE_USERS_ADMIN_PANEL_PERMISSION = 'lmsm_admin_panel_approve_users'
APPROVE_LOCATIONS_ADMIN_PANEL_PERMISSION = 'lmsm_admin_panel_approve_locations'
APPROVE_STOCK_MANAGEMENT_ADMIN_PANEL_PERMISSION = 'lmsm_admin_panel_approve_stock_management'

# Error messages
POI_TYPE_ALREADY_EXISTS = "The point of interest type already exists."
USER_DOES_NOT_EXIST = "The user does not exist."
GROUP_NOT_AVAILABLE = "The group is not available."
GROUP_DOES_NOT_EXIST = "The group does not exist."
USER_NOT_PROVIDED = "The user was not provided."
GROUP_NOT_PROVIDED = "The group was not provided."
EMAIL_NOT_PROVIDED = "The email was not provided."
REALM_ALREADY_EXISTS = "The realm already exists."
ORGANIZATION_DOES_NOT_EXIST = "The organization does not exist."
PARTNER_NOT_UNDER_ORGANIZATION = "The partner does not exist under the organization."
ITEMS_NOT_PROVIDED = "No items were provided."
INVALID_QUANTITY = "The quantity must be greater than 0."
UOM_NOT_PROVIDED = "The unit of measurement (UOM) was not provided."
UOM_NOT_VALID = "The unit of measurement (UOM) is not valid."
PARTNER_NOT_UNDER_LOCATION = "The partner does not exist under the location."
LAST_MILE_PROFILE_NOT_FOUND = "The last mile profile was not found."
STATUS_NOT_CRRECT = "The status should be in 'approved' or 'rejected'."

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
