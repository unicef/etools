from unittest import skip

from django.db import connection

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.partners import forms
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.users.tests.factories import UserFactory


@skip('TODO REALMS remove')
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

    # def test_clean_duplicate_email(self):
    #     """Duplicate email not allowed if user associated as staff member"""
    #     staff = PartnerStaffFactory()
    #     self.data["email"] = staff.user.email
    #     form = forms.PartnerStaffMemberForm(self.data)
    #     self.assertFalse(form.is_valid())
    #     self.assertIn(
    #         "This user already exists under a different partnership: {}".format(
    #             staff.user.email
    #         ),
    #         form.errors["__all__"]
    #     )

    def test_clean_user_exists(self):
        """Duplicate emails are ok, if user not unicef and not staff member already"""
        UserFactory(email="test@example.com")
        form = forms.PartnerStaffMemberForm(self.data)
        self.assertTrue(form.is_valid())

    def test_clean_duplicate_email_no_profile_unicef(self):
        """Duplicate emails are ok, if user not unicef and not staff member already"""
        UserFactory(email="test@example.com")
        form = forms.PartnerStaffMemberForm(self.data)
        self.assertFalse(form.is_valid())
        self.assertIn("Unable to associate staff member to UNICEF user", form.errors["__all__"])

    # def test_clean_email_change(self):
    #     """Email address may not be changed"""
    #     self.data["email"] = "change@example.com"
    #     partner = PartnerFactory()
    #     staff = PartnerStaffFactory(
    #         partner=partner,
    #         email="test@example.com",
    #     )
    #     form = forms.PartnerStaffMemberForm(self.data, instance=staff)
    #     self.assertFalse(form.is_valid())
    #     self.assertIn(
    #         "User emails cannot be changed, please remove the user and add another one: change@example.com",
    #         form.errors["__all__"]
    #     )
    #
    # def test_clean_email_no_change(self):
    #     """Ensure valid if no change in email """
    #     partner = PartnerFactory()
    #     staff = PartnerStaffFactory(
    #         partner=partner,
    #         email="test@example.com",
    #     )
    #     form = forms.PartnerStaffMemberForm(self.data, instance=staff)
    #     self.assertTrue(form.is_valid(), form.errors)
    #
    # def test_clean_activate(self):
    #     """If staff member made active, ensure user not already associated
    #     with another partner
    #     """
    #     user = UserFactory(email="test@example.com")
    #     partner = PartnerFactory()
    #     staff = PartnerStaffFactory(
    #         partner=partner,
    #         email="test@example.com",
    #         active=False,
    #         user=user,
    #     )
    #     form = forms.PartnerStaffMemberForm(self.data, instance=staff)
    #     self.assertTrue(form.is_valid(), form.errors)
    #
    # def test_clean_activate_already_active(self):
    #     user = UserFactory(email="test@example.com")
    #     partner = PartnerFactory()
    #     staff = PartnerStaffFactory(
    #         partner=partner,
    #         email="test@example.com",
    #         active=True,
    #         user=user,
    #     )
    #     self.assertEqual(connection.tenant, user.get_staff_member_country())
    #     form = forms.PartnerStaffMemberForm(self.data, instance=staff)
    #     self.assertTrue(form.is_valid())
    #
    # def test_clean_activate_invalid(self):
    #     """If staff member made active, invalid if user already associated
    #     with another partner
    #     """
    #     staff_mock = Mock(return_value=Country(name='fake country', id=-1))
    #
    #     user = UserFactory(email="test@example.com")
    #     partner = PartnerFactory()
    #     staff = PartnerStaffFactory(
    #         partner=partner,
    #         email="test@example.com",
    #         active=False,
    #         user=user,
    #     )
    #     form = forms.PartnerStaffMemberForm(self.data, instance=staff)
    #     with patch('etools.applications.users.models.User.get_staff_member_country', staff_mock):
    #         self.assertFalse(form.is_valid())
    #     self.assertIn(
    #         "User is associated with another staff member record in fake country",
    #         form.errors["email"]
    #     )
    #
    # def test_clean_deactivate(self):
    #     user = UserFactory(email="test@example.com")
    #     partner = PartnerFactory()
    #     self.data['active'] = False
    #     staff = PartnerStaffFactory(
    #         partner=partner,
    #         email="test@example.com",
    #         active=True,
    #         user=user,
    #     )
    #     form = forms.PartnerStaffMemberForm(self.data, instance=staff)
    #     self.assertTrue(form.is_valid())
    #
    # def test_clean_deactivate_prp_synced(self):
    #     user = UserFactory(email="test@example.com")
    #     partner = PartnerFactory()
    #     self.data['active'] = False
    #     staff = PartnerStaffFactory(
    #         partner=partner,
    #         email="test@example.com",
    #         active=True,
    #         user=user,
    #     )
    #     InterventionFactory(status=Intervention.SIGNED).partner_focal_points.add(staff)
    #     form = forms.PartnerStaffMemberForm(self.data, instance=staff)
    #     self.assertFalse(form.is_valid())

    def test_save_user_assigned(self):
        user = UserFactory(email="test@example.com", realms__data=[])
        # user.profile.countries_available.clear()

        form = forms.PartnerStaffMemberForm(self.data)
        self.assertTrue(form.is_valid())
        staff_member = form.save()
        self.assertEqual(staff_member.user, user)
        self.assertTrue(user.profile.countries_available.filter(id=connection.tenant.id).exists())

    def test_save_user_created(self):
        form = forms.PartnerStaffMemberForm(self.data)
        self.assertTrue(form.is_valid())
        staff_member = form.save()
        self.assertTrue(staff_member.user.profile.countries_available.filter(id=connection.tenant.id).exists())
