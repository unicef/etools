from django.utils.translation import ugettext_lazy as _

from rest_framework.exceptions import ValidationError


class ExternalUserValidator:
    def __call__(self, value):
        from etools.applications.tpm.tpmpartners.models import TPMPartnerStaffMember
        from etools.applications.audit.purchase_order.models import AuditorStaffMember

        # make sure user is not staff member
        tpm_staff_qs = TPMPartnerStaffMember.objects.filter(user__email=value)
        audit_staff = AuditorStaffMember.objects.filter(user__email=value)
        if tpm_staff_qs.exists() or audit_staff.exists():
            raise ValidationError(_("User is a staff member."))
