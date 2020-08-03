from django.utils.translation import ugettext_lazy as _

from rest_framework.exceptions import ValidationError


class ExternalUserValidator:
    def __call__(self, value):
        from etools.applications.audit.purchase_order.models import AuditorStaffMember
        from etools.applications.tpm.tpmpartners.models import TPMPartnerStaffMember

        # email cannot end with UNICEF domain
        if value.endswith("@unicef.org"):
            raise ValidationError(
                _("UNICEF email address not allowed for external user."),
            )

        # make sure user is not staff member
        tpm_staff_qs = TPMPartnerStaffMember.objects.filter(user__email=value)
        audit_staff = AuditorStaffMember.objects.filter(user__email=value)
        if tpm_staff_qs.exists() or audit_staff.exists():
            raise ValidationError(_("User is a staff member."))
