from etools_validator.exceptions import StateValidationError
from etools_validator.utils import check_required_fields, check_rigid_fields
from etools_validator.validation import CompleteValidation

from etools.applications.travel.permissions import ItineraryPermissions


class ItineraryValid(CompleteValidation):
    VALIDATION_CLASS = 'travel.Itinerary'
    PERMISSIONS_CLASS = ItineraryPermissions
    BASIC_VALIDATIONS = []
    VALID_ERRORS = {}

    def check_required_fields(self, itinerary):
        required_fields = [
            f for f in self.permissions['required']
            if self.permissions['required'][f] is True
        ]
        required_valid, field = check_required_fields(
            itinerary,
            required_fields,
        )
        if not required_valid:
            raise StateValidationError(
                ['Required fields not completed in {}: {}'.format(
                    itinerary.status,
                    field,
                )]
            )

    def check_rigid_fields(self, itinerary, related=False):
        # this can be set if running in a task and old_instance is not set
        if self.disable_rigid_check:
            return
        rigid_fields = [
            f for f in self.permissions['edit']
            if self.permissions['edit'][f] is False
        ]
        rigid_valid, field = check_rigid_fields(
            itinerary,
            rigid_fields,
            related=related,
        )
        if not rigid_valid:
            raise StateValidationError(
                ['Cannot change fields while in {}: {}'.format(
                    itinerary.status,
                    field,
                )]
            )

    def state_draft_valid(self, itinerary, user=None):
        self.check_required_fields(itinerary)
        self.check_rigid_fields(itinerary, related=True)
        return True

    def state_submission_review_valid(self, itinerary, user=None):
        self.check_required_fields(itinerary)
        self.check_rigid_fields(itinerary, related=True)
        return True

    def state_submitted_valid(self, itinerary, user=None):
        self.check_required_fields(itinerary)
        self.check_rigid_fields(itinerary, related=True)
        return True

    def state_approved_valid(self, itinerary, user=None):
        self.check_required_fields(itinerary)
        self.check_rigid_fields(itinerary, related=True)
        return True

    def state_review_valid(self, itinerary, user=None):
        self.check_required_fields(itinerary)
        self.check_rigid_fields(itinerary, related=True)
        return True

    def state_completed_valid(self, itinerary, user=None):
        self.check_required_fields(itinerary)
        self.check_rigid_fields(itinerary, related=True)
        return True

    def state_rejected_valid(self, itinerary, user=None):
        self.check_required_fields(itinerary)
        self.check_rigid_fields(itinerary, related=True)
        return True

    def state_cancelled_valid(self, itinerary, user=None):
        self.check_required_fields(itinerary)
        self.check_rigid_fields(itinerary, related=True)
        return True


def itinerary_illegal_transition(itinerary):
    return False
