# Maps group names to the app_labels whose audit log entries they can see.
# A user's visible entries = union of app_labels across all their active groups.
# Groups not listed here get no audit log visibility.
GROUP_TO_AUDIT_APP_LABELS = {
    # LMSM
    "LMSM HQ Admin": ["last_mile"],

    # RSS Admin (broad)
    "RSS": ["partners", "audit", "action_points", "field_monitoring", "tpm"],

    # UNICEF User (broad but scoped)
    "UNICEF User": [
        "partners", "audit", "action_points", "field_monitoring",
        "tpm", "t2f", "reports",
    ],
}
