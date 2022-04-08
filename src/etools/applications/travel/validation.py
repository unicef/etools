from etools_validator.exceptions import StateValidationError
from etools_validator.utils import check_required_fields, check_rigid_fields
from etools_validator.validation import CompleteValidation
from unicef_notification.utils import send_notification_with_template

from etools.applications.travel.permissions import TripPermissions


class TripValid(CompleteValidation):
    VALIDATION_CLASS = 'travel.Trip'
    PERMISSIONS_CLASS = TripPermissions
    BASIC_VALIDATIONS = []
    VALID_ERRORS = {}

    def check_required_fields(self, trip):
        required_fields = [
            f for f in self.permissions['required']
            if self.permissions['required'][f] is True
        ]
        required_valid, field = check_required_fields(
            trip,
            required_fields,
        )
        if not required_valid:
            raise StateValidationError(
                ['Required fields not completed in {}: {}'.format(
                    trip.status,
                    field,
                )]
            )

    def check_rigid_fields(self, trip, related=False):
        # this can be set if running in a task and old_instance is not set
        if self.disable_rigid_check:
            return
        rigid_fields = [
            f for f in self.permissions['edit']
            if self.permissions['edit'][f] is False
        ]
        rigid_valid, field = check_rigid_fields(
            trip,
            rigid_fields,
            related=related,
        )
        if not rigid_valid:
            raise StateValidationError(
                ['Cannot change fields while in {}: {}'.format(
                    trip.status,
                    field,
                )]
            )

    def state_draft_valid(self, trip, user=None):
        self.check_required_fields(trip)
        self.check_rigid_fields(trip, related=True)
        return True

    def state_submission_review_valid(self, trip, user=None):
        self.check_required_fields(trip)
        self.check_rigid_fields(trip, related=True)
        return True

    def state_submitted_valid(self, trip, user=None):
        self.check_required_fields(trip)
        self.check_rigid_fields(trip, related=True)
        return True

    def state_approved_valid(self, trip, user=None):
        self.check_required_fields(trip)
        self.check_rigid_fields(trip, related=True)
        return True

    def state_review_valid(self, trip, user=None):
        self.check_required_fields(trip)
        self.check_rigid_fields(trip, related=True)
        return True

    def state_completed_valid(self, trip, user=None):
        self.check_required_fields(trip)
        self.check_rigid_fields(trip, related=True)
        return True

    def state_rejected_valid(self, trip, user=None):
        self.check_required_fields(trip)
        self.check_rigid_fields(trip, related=True)
        return True

    def state_cancelled_valid(self, trip, user=None):
        self.check_required_fields(trip)
        self.check_rigid_fields(trip, related=True)
        return True


def trip_illegal_transition(trip):
    return False


def trip_subreview(trip, old_instance=None, user=None):
    send_notification_with_template(
        recipients=[trip.supervisor.email],
        template_name="travel/trip/subreview",
        context=trip.get_mail_context(user)
    )


def trip_submitted(trip, old_instance=None, user=None):
    send_notification_with_template(
        recipients=[trip.supervisor.email],
        template_name="travel/trip/submitted",
        context=trip.get_mail_context(user)
    )


def trip_rejected(trip, old_instance=None, user=None):
    send_notification_with_template(
        recipients=[trip.traveller.email],
        template_name="travel/trip/rejected",
        context=trip.get_mail_context(user)
    )


def trip_approved(trip, old_instance=None, user=None):
    send_notification_with_template(
        recipients=[trip.traveller.email],
        template_name="travel/trip/approved",
        context=trip.get_mail_context(user)
    )
