from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import datetime

from EquiTrack.factories import (
    AgreementFactory,
    PartnerFactory,
    PartnerStaffFactory,
    ProfileFactory,
    UserFactory,
)
from EquiTrack.tests.mixins import FastTenantTestCase
from partners import forms
from partners.models import Agreement, PartnerType


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


class TestAgreementForm(FastTenantTestCase):
    def setUp(self):
        super(TestAgreementForm, self).setUp()
        self.partner = PartnerFactory(
            partner_type=PartnerType.UN_AGENCY,
        )
        self.data = {
            "partner": self.partner.pk,
            "agreement_type": Agreement.MOU,
            "start": "2002-01-01",
            "end": "2002-02-01",
            "signed_by_partner_date": "2001-02-01",
            "signed_by_unicef_date": "2001-03-01",
        }

    def test_init(self):
        """If no instance, then authorized officers field should be disabled"""
        form = forms.AgreementForm()
        self.assertTrue(form.fields["authorized_officers"].disabled)
        self.assertFalse(form.fields["authorized_officers"].queryset)

    def test_init_partner(self):
        """Set authorized officers field if partner has staff members"""
        staff = PartnerStaffFactory(partner=self.partner)
        agreement = AgreementFactory(partner=self.partner)
        form = forms.AgreementForm(instance=agreement)
        self.assertFalse(form.fields["authorized_officers"].disabled)
        self.assertIn(staff, form.fields["authorized_officers"].queryset)

    def test_form(self):
        """Check valid form"""
        form = forms.AgreementForm(self.data)
        self.assertTrue(form.is_valid())

    def test_form_start_before_unicef_sign_date(self):
        """Start date must happen after latest signed date

        Check with signed unicef date the later date
        """
        self.data["signed_by_unicef_date"] = "2002-02-01"
        self.data["signed_by_partner_date"] = "2002-01-01"
        form = forms.AgreementForm(self.data)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "Start date must be greater than latest of signed by partner/UNICEF date",
            form.errors["start"]
        )

    def test_form_start_before_partner_sign_date(self):
        """Start date must happen after latest signed date

        Check with signed partner date the later date
        """
        self.data["signed_by_unicef_date"] = "2002-01-01"
        self.data["signed_by_partner_date"] = "2002-02-01"
        form = forms.AgreementForm(self.data)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "Start date must be greater than latest of signed by partner/UNICEF date",
            form.errors["start"]
        )

    def test_form_start_after_end(self):
        """Start date must be before end date"""
        self.data["start"] = "2002-03-01"
        form = forms.AgreementForm(self.data)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "End date must be greater than start date",
            form.errors["end"]
        )

    def test_form_ssfa_year_invalid(self):
        """SSFA agreement start and end must be within a year

        Check that if fails validation properly
        """
        self.data["end"] = "2003-03-01"
        self.data["agreement_type"] = Agreement.SSFA
        form = forms.AgreementForm(self.data)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "SSFA can not be more than a year",
            form.errors["__all__"]
        )

    def test_form_ssfa_year(self):
        """SSFA agreement start and end must be within a year

        Check that it passes validation
        """
        self.data["agreement_type"] = Agreement.SSFA
        form = forms.AgreementForm(self.data)
        self.assertTrue(form.is_valid())

    def test_form_pca_not_civil(self):
        """PCA agreement can only be for CSO partner types"""
        self.data["agreement_type"] = Agreement.PCA
        form = forms.AgreementForm(self.data)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "Only Civil Society Organizations can sign Programme Cooperation Agreements",
            form.errors["__all__"]
        )

    def test_agreement_type_changed_after_signed(self):
        """Agreement type cannot be changed after being signed"""
        self.data["partner"] = self.partner
        agreement = AgreementFactory(**self.data)
        self.data["partner"] = self.partner.pk
        self.data["agreement_type"] = Agreement.SSFA
        form = forms.AgreementForm(self.data, instance=agreement)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "Agreement type can not be changed once signed by UNICEF and partner",
            form.errors["__all__"]
        )

    def test_form_pca_multiple_agreements_invalid(self):
        """Partner can only have 1 active PCA agreement

        Check invalid if start date before end date of other PCA agreement
        """
        AgreementFactory(
            partner=self.partner,
            agreement_type=Agreement.PCA,
            start="2002-01-01",
            end="2002-02-01",
            signed_by_unicef_date="2001-12-01",
            signed_by_partner_date="2001-12-01",
            status=Agreement.SIGNED
        )
        self.data["agreement_type"] = Agreement.PCA
        form = forms.AgreementForm(self.data)
        self.assertFalse(form.is_valid())
        self.assertIn(
            "This partner can only have one active PCA agreement",
            form.errors["agreement_type"]
        )

    def test_form_pca_multiple_agreements(self):
        """Partner can only have 1 active PCA agreement

        Check valid if start date after end date of other PCA agreement
        """
        AgreementFactory(
            partner=self.partner,
            agreement_type=Agreement.PCA,
            start="2001-01-01",
            end="2001-01-02",
            signed_by_unicef_date="2000-12-01",
            signed_by_partner_date="2000-12-01",
            status=Agreement.SIGNED
        )
        self.partner.partner_type = PartnerType.CIVIL_SOCIETY_ORGANIZATION
        self.partner.save()
        self.data["agreement_type"] = Agreement.PCA
        next_year = datetime.date.today().year + 1
        self.data["start"] = "{}-03-01".format(next_year)
        self.data["end"] = "{}-04-01".format(next_year)
        form = forms.AgreementForm(self.data)
        self.assertTrue(form.is_valid())

    def test_form_pca_start_date_none_unicef_date(self):
        """For PCA agreement, if start date None set to latest signed date

        Only if both signed dates set
        """
        self.data["agreement_type"] = Agreement.PCA
        self.data.pop("start")
        self.partner.partner_type = PartnerType.CIVIL_SOCIETY_ORGANIZATION
        self.partner.save()
        form = forms.AgreementForm(self.data)
        self.assertTrue(form.is_valid())
        self.assertEqual(
            form.cleaned_data["start"],
            form.cleaned_data["signed_by_unicef_date"]
        )

    def test_form_pca_start_date_none_partner_date(self):
        """For PCA agreement, if start date None set to latest signed date

        Only if both signed dates set
        """
        self.data["agreement_type"] = Agreement.PCA
        self.data.pop("start")
        self.data["signed_by_partner_date"] = "2001-04-01"
        self.partner.partner_type = PartnerType.CIVIL_SOCIETY_ORGANIZATION
        self.partner.save()
        form = forms.AgreementForm(self.data)
        self.assertTrue(form.is_valid())
        self.assertEqual(
            form.cleaned_data["start"],
            form.cleaned_data["signed_by_partner_date"]
        )

    def test_form_pca_start_date_no_signed_date(self):
        """For PCA agreement, if start date None set to latest signed date

        No signed dates
        """
        self.data["agreement_type"] = Agreement.PCA
        self.data.pop("start")
        self.data.pop("signed_by_unicef_date")
        self.data.pop("signed_by_partner_date")
        self.partner.partner_type = PartnerType.CIVIL_SOCIETY_ORGANIZATION
        self.partner.save()
        form = forms.AgreementForm(self.data)
        self.assertTrue(form.is_valid())
