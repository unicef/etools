from etools_validator.exceptions import StateValidationError, TransitionError
from etools_validator.utils import check_required_fields, check_rigid_fields
from etools_validator.validation import CompleteValidation

from etools.applications.audit.models import UNICEFAuditFocalPoint
from etools.applications.psea.permissions import AssessmentPermissions


class AssessmentValid(CompleteValidation):
    VALIDATION_CLASS = 'psea.Assessment'
    PERMISSIONS_CLASS = AssessmentPermissions
    BASIC_VALIDATIONS = []
    VALID_ERRORS = {}

    def check_required_fields(self, assessment):
        required_fields = [
            f for f in self.permissions['required']
            if self.permissions['required'][f] is True
        ]
        required_valid, field = check_required_fields(
            assessment,
            required_fields,
        )
        if not required_valid:
            raise StateValidationError(
                ['Required fields not completed in {}: {}'.format(
                    assessment.status,
                    field,
                )]
            )

    def check_rigid_fields(self, assessment, related=False):
        # this can be set if running in a task and old_instance is not set
        if self.disable_rigid_check:
            return
        rigid_fields = [
            f for f in self.permissions['edit']
            if self.permissions['edit'][f] is False
        ]
        rigid_valid, field = check_rigid_fields(
            assessment,
            rigid_fields,
            related=related,
        )
        if not rigid_valid:
            raise StateValidationError(
                ['Cannot change fields while in {}: {}'.format(
                    assessment.status,
                    field,
                )]
            )

    def state_draft_valid(self, assessment, user=None):
        self.check_required_fields(assessment)
        self.check_rigid_fields(assessment, related=True)
        return True

    def state_assigned_valid(self, assessment, user=None):
        # make sure assessor has staff members assigned if vendor type
        if assessment.assessor.assessor_type == assessment.assessor.TYPE_VENDOR:
            if not assessment.assessor.auditor_firm_staff.exists():
                raise StateValidationError(["Staff member(s) required"])
        self.check_required_fields(assessment)
        self.check_rigid_fields(assessment, related=True)
        return True

    def state_in_progress_valid(self, assessment, user=None):
        self.check_required_fields(assessment)
        self.check_rigid_fields(assessment, related=True)
        return True

    def state_submitted_valid(self, assessment, user=None):
        # make the errors prettier for certain requirements that are more likely to be overlooked.
        if not assessment.assessment_date:
            raise StateValidationError(["Assessment Date is required to submit (Details -> Assessment Information ->"
                                        " Assessment Date)"])
        if not assessment.overall_rating:
            raise StateValidationError(["You must provide a rating to all indicators in order to submit"])
        self.check_required_fields(assessment)
        self.check_rigid_fields(assessment, related=True)
        return True

    def state_rejected_valid(self, assessment, user=None):
        self.check_required_fields(assessment)
        self.check_rigid_fields(assessment, related=True)
        return True

    def state_final_valid(self, assessment, user=None):
        self.check_required_fields(assessment)
        self.check_rigid_fields(assessment, related=True)
        return True

    # Allow cancel anytime?
    # def state_cancelled_valid(self, assessment, user=None):
    #     self.check_required_fields(assessment)
    #     self.check_rigid_fields(assessment, related=True)
    #     return True


def assessment_illegal_transition(assessment):
    return False


def assessment_focal_point_user(assessment, user):
    if not user.groups.filter(name__in=[UNICEFAuditFocalPoint.name]).count():
        raise TransitionError(
            ['Only Audit Focal Point can execute this transition']
        )
    return True


def assessment_user_belongs(assessment, user):
    return assessment.user_belongs(user)
