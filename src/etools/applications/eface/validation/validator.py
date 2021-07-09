from etools_validator.exceptions import StateValidationError
from etools_validator.utils import check_required_fields, check_rigid_fields
from etools_validator.validation import CompleteValidation

from etools.applications.eface.validation.permissions import EFaceFormPermissions


class EFaceFormValid(CompleteValidation):
    VALIDATION_CLASS = 'eface.EFaceForm'
    BASIC_VALIDATIONS = []
    VALID_ERRORS = {}

    PERMISSIONS_CLASS = EFaceFormPermissions

    def check_required_fields(self, form):
        required_fields = [f for f in self.permissions['required'] if self.permissions['required'][f]]
        required_valid, fields = check_required_fields(form, required_fields)
        if not required_valid:
            raise StateValidationError(['Required fields not completed in {}: {}'.format(
                form.status, ', '.join(f for f in fields))])

    def check_rigid_fields(self, form, related=False):
        # this can be set if running in a task and old_instance is not set
        if self.disable_rigid_check:
            return
        rigid_fields = [f for f in self.permissions['edit'] if not self.permissions['edit'][f]]
        rigid_valid, field = check_rigid_fields(form, rigid_fields, related=related)
        if not rigid_valid:
            raise StateValidationError(['Cannot change fields while in {}: {}'.format(form.status, field)])

    def state_draft_valid(self, instance, user=None):
        self.check_required_fields(instance)
        self.check_rigid_fields(instance, related=True)
        # reject_reason_provided(instance, self.old_status)
        return True

    def state_submitted_valid(self, instance, user=None):
        self.check_required_fields(instance)
        self.check_rigid_fields(instance, related=True)
        return True

    def state_unicef_approved_valid(self, instance, user=None):
        self.check_required_fields(instance)
        self.check_rigid_fields(instance, related=True)
        return True

    def state_finalized_valid(self, instance, user=None):
        self.check_required_fields(instance)
        self.check_rigid_fields(instance, related=True)
        return True

    def state_cancelled_valid(self, instance, user=None):
        # cancel_reason_provided(instance)
        return True
