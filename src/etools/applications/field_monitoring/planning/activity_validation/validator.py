from django.utils.translation import ugettext_lazy as _

from etools_validator.exceptions import StateValidationError, BasicValidationError
from etools_validator.utils import check_rigid_fields, check_required_fields
from etools_validator.validation import CompleteValidation

from etools.applications.field_monitoring.planning.activity_validation.permissions import ActivityPermissions
from etools.applications.field_monitoring.planning.models import MonitoringActivity


def staff_activity_has_no_tpm_partner(i):
    if i.activity_type == MonitoringActivity.TYPES.staff and i.tpm_partner:
        raise BasicValidationError(_('TPM Partner selected for staff activity'))
    return True


class ActivityValid(CompleteValidation):
    VALIDATION_CLASS = 'field_monitoring_planning.MonitoringActivity'
    BASIC_VALIDATIONS = [
        staff_activity_has_no_tpm_partner,
    ]

    VALID_ERRORS = {
        # 'suspended_expired_error': 'State suspended cannot be modified since the end date of '
        #                            'the intervention surpasses today',
    }

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

    def state_draft_valid(self, intervention, user=None):
        self.check_required_fields(intervention)
        self.check_rigid_fields(intervention, related=True)
        return True

    # def state_signed_valid(self, intervention, user=None):
    #     self.check_required_fields(intervention)
    #     self.check_rigid_fields(intervention, related=True)
    #     if intervention.contingency_pd is False and intervention.total_unicef_budget == 0:
    #         raise StateValidationError([_('UNICEF Cash $ or UNICEF Supplies $ should not be 0')])
    #     return True
