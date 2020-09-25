from unittest import skip

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners import forms
from etools.applications.partners.models import PartnerOrganization, PartnerType
from etools.applications.partners.tests.factories import PartnerFactory, PartnerStaffFactory
from etools.applications.users.tests.factories import UserFactory


class TestPartnersAdminForm(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        self.data = {
            "name": "Name",
            "partner_type": PartnerType.UN_AGENCY,
            "rating": "High",
            "type_of_assessment": PartnerOrganization.MICRO_ASSESSMENT,
        }

    def test_form(self):
        form = forms.PartnersAdminForm(self.data)
        self.assertTrue(form.is_valid())

    def test_clean_no_cso_type(self):
        self.data["partner_type"] = PartnerType.CIVIL_SOCIETY_ORGANIZATION
        form = forms.PartnersAdminForm(self.data)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "You must select a type for this CSO",
            form.errors["__all__"]
        )

    def test_clean_cso_type(self):
        self.data["cso_type"] = "National"
        form = forms.PartnersAdminForm(self.data)
        self.assertFalse(form.is_valid())
        self.assertIn(
            '"CSO Type" does not apply to non-CSO organizations, please remove type',
            form.errors["__all__"]
        )


class TestPartnerStaffMemberForm(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.partner = PartnerFactory()

    def setUp(self):
        super().setUp()
        self.data = {
            "email": "test@example.com",
            "partner": self.partner.pk,
            "first_name": "First",
            "last_name": "Last",
            "active": True,
        }

    def test_form(self):
        form = forms.PartnerStaffMemberForm(self.data)
        self.assertTrue(form.is_valid())

    def test_clean_not_active(self):
        """Staff member needs to be active"""
        self.data["active"] = False
        form = forms.PartnerStaffMemberForm(self.data)
        self.assertFalse(form.is_valid())
        self.assertIn("active", form.errors.keys())
        self.assertEqual(
            form.errors["active"],
            ["New Staff Member needs to be active at the moment of creation"]
        )

    def test_clean_duplicate_email(self):
        """Duplicate email not allowed if user associated as staff member"""
        staff = PartnerStaffFactory()
        self.data["email"] = staff.user.email
        form = forms.PartnerStaffMemberForm(self.data)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "This user already exists: {}".format(staff.user.email),
            form.errors["__all__"]
        )

    def test_clean_duplicate_email_no_profile(self):
        """Duplicate emails are ok, if user not staff member already"""
        UserFactory(email="test@example.com")
        form = forms.PartnerStaffMemberForm(self.data)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "This user already exists: {}".format("test@example.com"),
            form.errors["__all__"]
        )

    def test_clean_email_change(self):
        """Email address may not be changed"""
        self.data["email"] = "change@example.com"
        partner = PartnerFactory()
        staff = PartnerStaffFactory(
            partner=partner,
            email="test@example.com",
        )
        form = forms.PartnerStaffMemberForm(self.data, instance=staff)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "User emails cannot be changed, please remove the user and add another one: change@example.com",
            form.errors["__all__"]
        )

    def test_clean_email_no_change(self):
        """Ensure valid if no change in email """
        partner = PartnerFactory()
        staff = PartnerStaffFactory(
            partner=partner,
            email="test@example.com",
        )
        form = forms.PartnerStaffMemberForm(self.data, instance=staff)
        self.assertTrue(form.is_valid(), form.errors)

    def test_clean_activate(self):
        """If staff member made active, ensure user not already associated
        with another partner
        """
        user = UserFactory(email="test@example.com")
        partner = PartnerFactory()
        staff = PartnerStaffFactory(
            partner=partner,
            email="test@example.com",
            active=False,
            user=user,
        )
        form = forms.PartnerStaffMemberForm(self.data, instance=staff)
        self.assertTrue(form.is_valid(), form.errors)
