from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from unicef_djangolib.forms import AutoSizeTextForm

from etools.applications.organizations.models import Organization
from etools.applications.partners.models import OrganizationType


class OrganizationAdminForm(AutoSizeTextForm):

    class Meta:
        model = Organization
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()

        organization_type = cleaned_data.get('organization_type')
        cso_type = cleaned_data.get('cso_type')

        if organization_type and organization_type == OrganizationType.CIVIL_SOCIETY_ORGANIZATION and not cso_type:
            raise ValidationError(
                _('You must select a type for this CSO')
            )
        if organization_type and organization_type != OrganizationType.CIVIL_SOCIETY_ORGANIZATION and cso_type:
            raise ValidationError(
                _('"CSO Type" does not apply to non-CSO organizations, please remove type')
            )
        return cleaned_data
