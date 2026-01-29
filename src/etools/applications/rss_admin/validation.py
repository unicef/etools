from django.utils.translation import gettext as _

from etools_validator.exceptions import StateValidationError
from etools_validator.utils import check_rigid_fields

from etools.applications.partners.validation.agreements import AgreementValid
from etools.applications.partners.validation.interventions import InterventionValid


class _RelaxRigidMixin:
    """Mixin to relax specific rigid fields while preserving base validations."""

    RELAXED_FIELDS = set()

    def check_rigid_fields(self, instance, related=False):
        if self.disable_rigid_check:
            return
        rigid_fields = [f for f in self.permissions['edit'] if self.permissions['edit'][f] is False]
        # Drop relaxed fields from the rigid set
        if self.RELAXED_FIELDS:
            rigid_fields = [f for f in rigid_fields if f not in self.RELAXED_FIELDS]

        rigid_valid, field = check_rigid_fields(instance, rigid_fields, related=related)
        if not rigid_valid:
            raise StateValidationError([
                _('Cannot change fields while in %(status)s: %(field)s')
                % {'status': getattr(instance, 'status', ''), 'field': field}
            ])


class RssAgreementValid(_RelaxRigidMixin, AgreementValid):
    """RSS Admin Agreement validator that allows fixing signature dates and incomplete agreements."""

    RELAXED_FIELDS = {'signed_by_unicef_date', 'signed_by_partner_date'}

    def check_required_fields(self, agreement):
        """Skip required field validation for RSS Admin when status isn't changing."""
        if self.old and self.old.status == agreement.status:
            # Status not changing, allow updates to fix incomplete agreements
            return
        # Status is changing or new instance, run normal validation
        return super().check_required_fields(agreement)


class RssInterventionValid(_RelaxRigidMixin, InterventionValid):
    """RSS Admin Intervention validator that allows fixing signature dates and incomplete interventions."""

    RELAXED_FIELDS = {'signed_by_unicef_date', 'signed_by_partner_date'}

    def check_required_fields(self, intervention):
        """Skip required field validation for RSS Admin when status isn't changing."""
        if self.old and self.old.status == intervention.status:
            # Status not changing, allow updates to fix incomplete interventions
            return
        # Status is changing or new instance, run normal validation
        return super().check_required_fields(intervention)
