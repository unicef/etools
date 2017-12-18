from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from EquiTrack.tests.mixins import FastTenantTestCase
from partners import forms
from partners.models import PartnerType
from partners.tests.factories import PartnerFactory, PartnerStaffFactory
from users.tests.factories import ProfileFactory, UserFactory


class TestPartnersAdminForm(FastTenantTestCase):
    def setUp(self):
        super(TestPartnersAdminForm, self).setUp()
        self.data = {
            "name": "Name",
            "partner_type": PartnerType.UN_AGENCY,
            "rating": "Strong",
            "shared_partner": "No",
            "type_of_assessment": "Normal",
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


class TestPartnerStaffMemberForm(FastTenantTestCase):
    def setUp(self):
        super(TestPartnerStaffMemberForm, self).setUp()
        partner = PartnerFactory()
        self.data = {
            "email": "test@example.com",
            "partner": partner.pk,
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
        profile = ProfileFactory(
            partner_staff_member=10,
        )
        self.data["email"] = profile.user.email
        form = forms.PartnerStaffMemberForm(self.data)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "This user already exists under a different partnership: {}".format(
                profile.user.email
            ),
            form.errors["__all__"]
        )

    def test_clean_duplicate_email_no_profile(self):
        """Duplicate emails are ok, if user not staff member already"""
        UserFactory(email="test@example.com")
        form = forms.PartnerStaffMemberForm(self.data)
        self.assertTrue(form.is_valid())

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
        self.assertTrue(form.is_valid())

    def test_clean_activate(self):
        """If staff member made active, ensure user not already associated
        with another partner
        """
        UserFactory(email="test@example.com")
        partner = PartnerFactory()
        staff = PartnerStaffFactory(
            partner=partner,
            email="test@example.com",
            active=False
        )
        form = forms.PartnerStaffMemberForm(self.data, instance=staff)
        self.assertTrue(form.is_valid())

    def test_clean_activate_invalid(self):
        """If staff member made active, invalid if user already associated
        with another partner
        """
        profile = ProfileFactory(
            partner_staff_member=10,
        )
        partner = PartnerFactory()
        staff = PartnerStaffFactory(
            partner=partner,
            email=profile.user.email,
            active=False
        )
        self.data["email"] = profile.user.email
        form = forms.PartnerStaffMemberForm(self.data, instance=staff)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "The Partner Staff member you are trying to activate is associated with a different partnership",
            form.errors["active"]
        )
