from django.utils.translation import gettext as _

from etools_validator.exceptions import StateValidationError
from etools_validator.utils import check_required_fields, check_rigid_fields
from etools_validator.validation import CompleteValidation

from etools.applications.field_monitoring.planning.activity_validation.permissions import ActivityPermissions
from etools.applications.field_monitoring.planning.activity_validation.validations.basic import (
    interventions_connected_with_partners,
    staff_activity_has_no_tpm_partner,
    tpm_staff_members_belongs_to_the_partner,
)
from etools.applications.field_monitoring.planning.activity_validation.validations.state import (
    activity_overall_findings_required,
    activity_questions_required,
    at_least_one_item_added,
    cancel_reason_provided,
    reject_reason_provided,
    report_reject_reason_provided,
    started_checklists_required,
    tpm_partner_is_assigned_for_tpm_activity,
)


class ActivityValid(CompleteValidation):
    VALIDATION_CLASS = 'field_monitoring_planning.MonitoringActivity'
    BASIC_VALIDATIONS = [
        staff_activity_has_no_tpm_partner,
        tpm_staff_members_belongs_to_the_partner,
        interventions_connected_with_partners,
        # interventions_connected_with_cp_outputs,
    ]

    VALID_ERRORS = {}

    PERMISSIONS_CLASS = ActivityPermissions

    def get_permissions(self, instance):
        instance.old = self.old
        return super().get_permissions(instance)

    def check_required_fields(self, intervention):
        required_fields = [f for f in self.permissions['required'] if self.permissions['required'][f]]
        required_valid, fields = check_required_fields(intervention, required_fields)
        if not required_valid:
            raise StateValidationError([_('Required fields not completed in %(status)s: %(fields)s')
                                        % {'status': intervention.status,
                                           'fields': ', '.join(f for f in fields)
                                           }
                                        ])

    def check_rigid_fields(self, intervention, related=False):
        # this can be set if running in a task and old_instance is not set
        if self.disable_rigid_check:
            return
        rigid_fields = [f for f in self.permissions['edit'] if not self.permissions['edit'][f]]
        rigid_valid, field = check_rigid_fields(intervention, rigid_fields, related=related)
        if not rigid_valid:
            raise StateValidationError([_('Cannot change fields while in %(status)s: %(field)s')
                                        % {'status': intervention.status,
                                           'field': field
                                           }
                                        ])

    def state_draft_valid(self, instance, user=None):
        self.check_required_fields(instance)
        self.check_rigid_fields(instance, related=True)
        reject_reason_provided(instance, self.old_status)
        return True

    def state_checklist_valid(self, instance, user=None):
        self.check_required_fields(instance)
        self.check_rigid_fields(instance, related=True)
        at_least_one_item_added(instance)
        return True

    def state_review_valid(self, instance, user=None):
        self.check_required_fields(instance)
        self.check_rigid_fields(instance, related=True)
        activity_questions_required(instance)
        return True

    def state_assigned_valid(self, instance, user=None):
        self.check_required_fields(instance)
        self.check_rigid_fields(instance, related=True)
        tpm_partner_is_assigned_for_tpm_activity(instance)
        report_reject_reason_provided(instance, self.old_status)
        return True

    def state_data_collection_valid(self, instance, user=None):
        self.check_required_fields(instance)
        self.check_rigid_fields(instance, related=True)
        return True

    def state_report_finalization_valid(self, instance, user=None):
        self.check_required_fields(instance)
        self.check_rigid_fields(instance, related=True)
        started_checklists_required(instance)
        return True

    def state_submitted_valid(self, instance, user=None):
        self.check_required_fields(instance)
        self.check_rigid_fields(instance, related=True)
        activity_overall_findings_required(instance)
        return True

    def state_completed_valid(self, instance, user=None):
        self.check_required_fields(instance)
        self.check_rigid_fields(instance, related=True)
        return True

    def state_cancelled_valid(self, instance, user=None):
        cancel_reason_provided(instance)
        return True
