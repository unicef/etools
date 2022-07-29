from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.organizations import forms
from etools.applications.organizations.models import OrganizationType


class TestPartnersAdminForm(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        self.data = {
            "name": "Name",
            "vendor_number": "Unique Vendor no.",
            "organization_type": OrganizationType.UN_AGENCY,
        }

    def test_form(self):
        form = forms.OrganizationAdminForm(self.data)
        self.assertTrue(form.is_valid())

    def test_clean_no_cso_type(self):
        self.data["organization_type"] = OrganizationType.CIVIL_SOCIETY_ORGANIZATION
        form = forms.OrganizationAdminForm(self.data)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "You must select a type for this CSO",
            form.errors["__all__"]
        )

    def test_clean_cso_type(self):
        self.data["cso_type"] = "National"
        form = forms.OrganizationAdminForm(self.data)
        self.assertFalse(form.is_valid())
        self.assertIn(
            '"CSO Type" does not apply to non-CSO organizations, please remove type',
            form.errors["__all__"]
        )
