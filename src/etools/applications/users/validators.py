from django.contrib.auth import get_user_model
from django.db import connection
from django.utils.translation import gettext_lazy as _

from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueValidator

from etools.applications.users.models import Realm


class ExternalUserValidator:
    def __call__(self, value):
        # email cannot end with UNICEF domain
        if value.endswith("@unicef.org"):
            raise ValidationError(
                _("UNICEF email address not allowed for external user."),
            )

        if value != value.lower():
            raise ValidationError(_("Email needs to be lower case."))

        # make sure user is not staff member
        tpm_staff_qs = Realm.objects.filter(
            user__email=value,
            country=connection.tenant,
            organization__tpmpartner__isnull=False,
        )
        audit_staff = Realm.objects.filter(
            user__email=value,
            country=connection.tenant,
            organization__auditorfirm__isnull=False,
        )
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
