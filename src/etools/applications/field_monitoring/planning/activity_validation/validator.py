from etools_validator.exceptions import StateValidationError
from etools_validator.utils import check_rigid_fields, check_required_fields
from etools_validator.validation import CompleteValidation

from etools.applications.field_monitoring.planning.activity_validation.permissions import ActivityPermissions
from etools.applications.field_monitoring.planning.activity_validation.validations.basic import \
    tpm_staff_members_belongs_to_the_partner, staff_activity_has_no_tpm_partner
from etools.applications.field_monitoring.planning.activity_validation.validations.state import \
    tpm_partner_is_assigned_for_tpm_activity, at_least_one_item_added


class ActivityValid(CompleteValidation):
    VALIDATION_CLASS = 'field_monitoring_planning.MonitoringActivity'
    BASIC_VALIDATIONS = [
        staff_activity_has_no_tpm_partner,
        tpm_staff_members_belongs_to_the_partner,
    ]

    VALID_ERRORS = {}

    PERMISSIONS_CLASS = ActivityPermissions

    def check_required_fields(self, intervention):
        required_fields = [f for f in self.permissions['required'] if self.permissions['required'][f] is True]
        required_valid, fields = check_required_fields(intervention, required_fields)
        if not required_valid:
            raise StateValidationError(['Required fields not completed in {}: {}'.format(
                intervention.status, ', '.join(f for f in fields))])

    def check_rigid_fields(self, intervention, related=False):
        # this can be set if running in a task and old_instance is not set
        if self.disable_rigid_check:
            return
        rigid_fields = [f for f in self.permissions['edit'] if self.permissions['edit'][f] is False]
        rigid_valid, field = check_rigid_fields(intervention, rigid_fields, related=related)
        if not rigid_valid:
            raise StateValidationError(['Cannot change fields while in {}: {}'.format(intervention.status, field)])

    def state_draft_valid(self, instance, user=None):
        self.check_required_fields(instance)
        self.check_rigid_fields(instance, related=True)
        return True

    def state_details_configured_valid(self, instance, user=None):
        self.check_required_fields(instance)
        self.check_rigid_fields(instance, related=True)
        tpm_partner_is_assigned_for_tpm_activity(instance)
        at_least_one_item_added(instance)
        return True
