import datetime

from EquiTrack.factories import (
    AgreementAmendmentFactory,
    AgreementFactory,
    CountryProgrammeFactory,
    PartnerFactory,
    PartnerStaffFactory,
    UserFactory,
)
from EquiTrack.tests.mixins import FastTenantTestCase as TenantTestCase
from EquiTrack.validation_mixins import BasicValidationError, TransitionError
from partners.models import Agreement
from partners.validation import agreements


class TestAgreementTransitionToSignedValid(TenantTestCase):
    def test_invalid_pca(self):
        """The agreement transition validation fails if;
        - Agreement type is PCA
        AND there exists an agreement that has ALL of the following;
        - same partner
        - status is SIGNED
        - agreement type is PCA
        - same country programme
        - start date > 2015-07-01
        """
        partner = PartnerFactory()
        country = CountryProgrammeFactory()
        AgreementFactory(
            partner=partner,
            agreement_type=Agreement.PCA,
            status=Agreement.SIGNED,
            country_programme=country,
            start=datetime.date.today()
        )
        agreement = AgreementFactory(
            partner=partner,
            agreement_type=Agreement.PCA,
            country_programme=country,
        )

        with self.assertRaises(TransitionError):
            agreements.agreement_transition_to_signed_valid(agreement)

    def test_invalid_no_start(self):
        """Agreement transition validation fails if no start date"""
        agreement = AgreementFactory(
            agreement_type=Agreement.MOU,
        )
        with self.assertRaises(TransitionError):
            agreements.agreement_transition_to_signed_valid(agreement)

    def test_invalid_no_end(self):
        """Agreement transition validation fails if no end date"""
        agreement = AgreementFactory(
            agreement_type=Agreement.MOU,
            start=datetime.date.today()
        )
        with self.assertRaises(TransitionError):
            agreements.agreement_transition_to_signed_valid(agreement)

    def test_valid(self):
        agreement = AgreementFactory(
            agreement_type=Agreement.MOU,
            start=datetime.date.today(),
            end=datetime.date.today(),
        )
        self.assertTrue(
            agreements.agreement_transition_to_signed_valid(agreement)
        )


class TestAgreementTransitionToEndedValid(TenantTestCase):
    def test_invalid(self):
        agreement = AgreementFactory(
            status=Agreement.DRAFT,
        )
        with self.assertRaises(TransitionError):
            agreements.agreement_transition_to_ended_valid(agreement)

    def test_valid(self):
        agreement = AgreementFactory(
            agreement_type=Agreement.MOU,
            status=Agreement.SIGNED,
            start=datetime.date(2001, 1, 1),
            end=datetime.date(2001, 1, 2),
        )
        self.assertEqual(agreement.status, Agreement.SIGNED)
        self.assertTrue(agreement.end)
        self.assertTrue(agreement.end < datetime.date.today())
        self.assertTrue(
            agreements.agreement_transition_to_ended_valid(agreement)
        )


class TestAgreementsIllegalTransition(TenantTestCase):
    def test_false(self):
        agreement = AgreementFactory()
        self.assertFalse(agreements.agreements_illegal_transition(agreement))


class TestAgreementsIllegalTransitionPermissions(TenantTestCase):
    def test_true(self):
        agreement = AgreementFactory()
        agreement.old_instance = None
        self.assertTrue(
            agreements.agreements_illegal_transition_permissions(
                agreement,
                None
            )
        )

    def test_assert(self):
        """If no old_instance attribute set on agreement, raise an exception"""
        agreement = AgreementFactory()
        with self.assertRaises(AssertionError):
            agreements.agreements_illegal_transition_permissions(
                agreement,
                None
            )


class TestAmendmentsValid(TenantTestCase):
    def test_invalid_name(self):
        agreement = AgreementFactory()
        AgreementAmendmentFactory(
            agreement=agreement,
        )
        self.assertFalse(agreements.amendments_valid(agreement))

    def test_invalid_date(self):
        agreement = AgreementFactory()
        AgreementAmendmentFactory(
            agreement=agreement,
            signed_amendment='fake.pdf'
        )
        self.assertFalse(agreements.amendments_valid(agreement))

    def test_valid(self):
        agreement = AgreementFactory()
        AgreementAmendmentFactory(
            agreement=agreement,
            signed_amendment='fake.pdf',
            signed_date=datetime.date.today(),
        )
        self.assertTrue(agreements.amendments_valid(agreement))


class TestStartEndDatesValid(TenantTestCase):
    def test_invalid(self):
        agreement = AgreementFactory(
            agreement_type=Agreement.MOU,
            start=datetime.date.today(),
            end=datetime.date.today() - datetime.timedelta(days=1),
        )
        self.assertFalse(agreements.start_end_dates_valid(agreement))

    def test_valid(self):
        agreement = AgreementFactory(
            start=datetime.date.today() - datetime.timedelta(days=1),
            end=datetime.date.today(),
        )
        self.assertTrue(agreements.start_end_dates_valid(agreement))


class TestSignedByEveryoneValid(TenantTestCase):
    def test_invalid(self):
        agreement = AgreementFactory(
            agreement_type=Agreement.MOU,
            signed_by_unicef_date=datetime.date.today(),
            signed_by_partner_date=None,
        )
        self.assertFalse(agreements.signed_by_everyone_valid(agreement))

    def test_valid(self):
        agreement = AgreementFactory(
            signed_by_partner_date=datetime.date.today(),
            signed_by_unicef_date=datetime.date.today(),
        )
        self.assertTrue(agreements.signed_by_everyone_valid(agreement))


class TestSignaturesValid(TenantTestCase):
    def test_exception(self):
        agreement = AgreementFactory(
            agreement_type=Agreement.SSFA,
            signed_by_unicef_date=datetime.date.today(),
        )
        with self.assertRaises(BasicValidationError):
            agreements.signatures_valid(agreement)

    def test_invalid(self):
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        partner = PartnerFactory()
        user = UserFactory()
        staff = PartnerStaffFactory(
            partner=partner,
        )
        agreement = AgreementFactory(
            partner=partner,
            signed_by_unicef_date=datetime.date.today(),
            signed_by=user,
            signed_by_partner_date=tomorrow,
            partner_manager=staff,
        )
        self.assertFalse(agreements.signatures_valid(agreement))

    def test_valid(self):
        partner = PartnerFactory()
        user = UserFactory()
        staff = PartnerStaffFactory(
            partner=partner,
        )
        agreement = AgreementFactory(
            partner=partner,
            signed_by_unicef_date=datetime.date.today(),
            signed_by=user,
            signed_by_partner_date=datetime.date.today(),
            partner_manager=staff,
        )
        self.assertTrue(agreements.signatures_valid(agreement))
