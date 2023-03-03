from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueValidator


class ExternalUserValidator:
    def __call__(self, value):
        from etools.applications.audit.purchase_order.models import AuditorStaffMember
        from etools.applications.tpm.tpmpartners.models import TPMPartnerStaffMember

        # email cannot end with UNICEF domain
        if value.endswith("@unicef.org"):
            raise ValidationError(
                _("UNICEF email address not allowed for external user."),
            )

        if value != value.lower():
            raise ValidationError(_("Email needs to be lower case."))

        # make sure user is not staff member
        tpm_staff_qs = TPMPartnerStaffMember.objects.filter(user__email=value)
        audit_staff = AuditorStaffMember.objects.filter(user__email=value)
        if tpm_staff_qs.exists() or audit_staff.exists():
            raise ValidationError(_("User is a staff member."))


class EmailValidator(UniqueValidator):
    def __init__(self, queryset=None):
        if queryset is None:
            queryset = get_user_model().objects.all()
        super().__init__(
            queryset,
            message="This user already exists in the system.",
        )


class LowerCaseEmailValidator:
    def __call__(self, value):
        if value != value.lower():
            raise ValidationError(_("Email needs to be lower case."))
