import datetime
from unittest import skip
from unittest.mock import Mock, patch

from etools_validator.exceptions import BasicValidationError, StateValidationError, TransitionError

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.funds.tests.factories import FundsReservationHeaderFactory
from etools.applications.partners.models import Agreement, FileType, Intervention, InterventionAmendment
from etools.applications.partners.tests.factories import (
    AgreementFactory,
    InterventionAmendmentFactory,
    InterventionAttachmentFactory,
    InterventionFactory,
    PartnerStaffFactory,
)
from etools.applications.partners.validation.interventions import (
    InterventionValid,
    partnership_manager_only,
    signed_date_valid,
    ssfa_agreement_has_no_other_intervention,
    start_date_related_agreement_valid,
    start_date_signed_valid,
    transition_ok,
    transition_to_active,
    transition_to_closed,
    transition_to_signed,
    transition_to_suspended,
    transition_to_terminated,
)
from etools.applications.users.tests.factories import GroupFactory, UserFactory


class TestPartnershipManagerOnly(BaseTenantTestCase):
    def test_manager_no_groups(self):
        user = UserFactory()
        with self.assertRaises(TransitionError):
            partnership_manager_only(None, user)

    def test_manager(self):
        user = UserFactory()
        user.groups.add(GroupFactory(name="Partnership Manager"))
        self.assertTrue(partnership_manager_only(None, user))


class TestTransitionOk(BaseTenantTestCase):
    def test_ok(self):
        self.assertTrue(transition_ok(None))


class TestTransitionToClosed(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        self.intervention = InterventionFactory(end=datetime.date(2001, 1, 1))
        self.expected = {
            'total_frs_amt': 0,
            'total_frs_amt_usd': 0,
            'total_outstanding_amt': 0,
            'total_outstanding_amt_usd': 0,
            'total_intervention_amt': 0,
            'total_actual_amt': 0,
            'total_actual_amt_usd': 0,
            'earliest_start_date': None,
            'latest_end_date': None,
            'total_completed_flag': False,
        }

    def assertFundamentals(self, data):
        assert data.keys() == self.expected.keys()
        for k, v in data.items():
            self.assertEqual(v, self.expected[k])

    def test_end_after_today(self):
        """End date cannot be after today's date'"""
        intervention = InterventionFactory(
            end=datetime.date.today() + datetime.timedelta(days=2)
        )
        with self.assertRaisesRegexp(
                TransitionError,
                "End date is in the future"
        ):
            transition_to_closed(intervention)
        self.expected["total_completed_flag"] = True
        self.assertFundamentals(intervention.total_frs)

    def test_total_amounts_outstanding_not_zero(self):
        """Total amounts must equal and total outstanding must be zero"""
        frs = FundsReservationHeaderFactory(
            intervention=self.intervention,
            total_amt=0.00,
            total_amt_local=10.00,
            intervention_amt=10.00,
            actual_amt=0.00,
            actual_amt_local=10.00,
            outstanding_amt_local=5.00,
            outstanding_amt=0.00
        )
        with self.assertRaisesRegexp(
                TransitionError,
                'Total FR amount needs to equal total actual amount, and '
                'Total Outstanding DCTs need to equal to 0'
        ):
            transition_to_closed(self.intervention)
        self.expected["total_outstanding_amt"] = 5.00
        self.expected["total_intervention_amt"] = 10.00
        self.expected["total_frs_amt"] = 10.00
        self.expected["total_actual_amt"] = 10.00
        self.expected["earliest_start_date"] = frs.start_date
        self.expected["latest_end_date"] = frs.end_date
        self.assertFundamentals(self.intervention.total_frs)

    def test_total_amounts_not_equal(self):
        """Total amounts must equal and total outstanding must be zero"""
        frs = FundsReservationHeaderFactory(
            intervention=self.intervention,
            total_amt=0.00,
            total_amt_local=10.00,
            intervention_amt=10.00,
            actual_amt_local=20.00,
            actual_amt=0.00,
            outstanding_amt_local=0.00,
            outstanding_amt=0.00,
        )
        with self.assertRaisesRegexp(
                TransitionError,
                'Total FR amount needs to equal total actual amount, and '
                'Total Outstanding DCTs need to equal to 0'
        ):
            transition_to_closed(self.intervention)
        self.expected["total_frs_amt"] = 10.00
        self.expected["total_intervention_amt"] = 10.00
        self.expected["total_actual_amt"] = 20.00
        self.expected["earliest_start_date"] = frs.start_date
        self.expected["latest_end_date"] = frs.end_date
        self.assertFundamentals(self.intervention.total_frs)

    def test_completed_total_amounts_not_zero(self):
        """Total outstanding must be zero for completed"""
        frs = FundsReservationHeaderFactory(
            intervention=self.intervention,
            total_amt=0.00,
            total_amt_local=10.00,
            intervention_amt=10.00,
            actual_amt_local=20.00,
            actual_amt=0.00,
            outstanding_amt_local=20.00,
            outstanding_amt=20.00,
            completed_flag=True,
        )
        with self.assertRaisesRegexp(
                TransitionError,
                'Total Outstanding DCTs need to equal to 0'
        ):
            transition_to_closed(self.intervention)
        self.expected["total_frs_amt"] = 10.00
        self.expected["total_intervention_amt"] = 10.00
        self.expected["total_actual_amt"] = 20.00
        self.expected["total_outstanding_amt"] = 20.00
        self.expected["total_outstanding_amt_usd"] = 20.00
        self.expected["earliest_start_date"] = frs.start_date
        self.expected["latest_end_date"] = frs.end_date
        self.expected["total_completed_flag"] = True
        self.assertFundamentals(self.intervention.total_frs)

    def test_total_amounts_valid(self):
        """Total amounts must equal and total outstanding must be zero"""
        frs = FundsReservationHeaderFactory(
            intervention=self.intervention,
            total_amt=0.00,
            total_amt_local=10.00,
            intervention_amt=0.00,
            actual_amt=0.00,
            actual_amt_local=10.00,
            outstanding_amt=0.00,
            outstanding_amt_local=0.00
        )
        self.assertTrue(transition_to_closed(self.intervention))
        self.expected["total_frs_amt"] = 10.00
        self.expected["total_actual_amt"] = 10.00
        self.expected["earliest_start_date"] = frs.start_date
        self.expected["latest_end_date"] = frs.end_date
        self.assertFundamentals(self.intervention.total_frs)

    def test_final_review_flag_invalid(self):
        """If Total actual amount > 100,000 need final_review_approved=True
        """
        frs = FundsReservationHeaderFactory(
            intervention=self.intervention,
            total_amt=0.00,
            total_amt_local=120000.00,
            actual_amt_local=120000.00,
            actual_amt=120000.00,
            outstanding_amt_local=0.00,
            outstanding_amt=0.00,
            intervention_amt=0.00,
        )

        with self.assertRaisesRegexp(
                TransitionError,
                'Final Review must be approved for documents having amount transferred greater than 100,000'
        ):
            transition_to_closed(self.intervention)
        self.expected["total_actual_amt"] = 120000.00
        self.expected["total_actual_amt_usd"] = 120000.00
        self.expected["total_frs_amt"] = 120000.00
        self.expected["earliest_start_date"] = frs.start_date
        self.expected["latest_end_date"] = frs.end_date
        self.assertFundamentals(self.intervention.total_frs)

    def test_final_review_flag(self):
        """If Total actual amount > 100,000 need attachment with
        type Final Partnership Review
        """
        self.intervention.final_review_approved = True
        self.intervention.save()
        frs = FundsReservationHeaderFactory(
            intervention=self.intervention,
            total_amt=0.00,
            total_amt_local=120000.00,
            actual_amt_local=120000.00,
            actual_amt=0,
            outstanding_amt_local=0.00,
            outstanding_amt=0.00,
            intervention_amt=0.00,
        )
        self.assertTrue(transition_to_closed(self.intervention))
        self.expected["total_actual_amt"] = 120000.00
        self.expected["total_frs_amt"] = 120000.00
        self.expected["earliest_start_date"] = frs.start_date
        self.expected["latest_end_date"] = frs.end_date
        self.assertFundamentals(self.intervention.total_frs)

    def test_total_frs_amount(self):
        """Ensure total_frs_amt set correctly"""
        frs = FundsReservationHeaderFactory(
            intervention=self.intervention,
            total_amt=0.00,
            total_amt_local=100.00,
            actual_amt=0.00,
            actual_amt_local=100.00,
            intervention_amt=0.00,
            outstanding_amt=0.00,
            outstanding_amt_local=0.00,
        )
        self.assertTrue(transition_to_closed(self.intervention))
        self.expected["total_frs_amt"] = 100.00
        self.expected["total_actual_amt"] = 100.00
        self.expected["earliest_start_date"] = frs.start_date
        self.expected["latest_end_date"] = frs.end_date
        self.assertFundamentals(self.intervention.total_frs)

    def test_dates(self):
        """Ensure earliest and latest dates set correctly"""
        FundsReservationHeaderFactory(
            intervention=self.intervention,
            fr_number=1,
            total_amt=0.00,
            total_amt_local=100.00,
            start_date=datetime.date(2001, 1, 1),
            end_date=datetime.date(2001, 2, 1),
            actual_amt=0.00,
            actual_amt_local=100.00,
            intervention_amt=0.00,
            outstanding_amt_local=0.00,
            outstanding_amt=0.00,
        )
        FundsReservationHeaderFactory(
            intervention=self.intervention,
            fr_number=2,
            total_amt=0.00,
            total_amt_local=100.00,
            start_date=datetime.date(2000, 1, 1),
            end_date=datetime.date(2000, 2, 1),
            actual_amt=0.00,
            actual_amt_local=100.00,
            intervention_amt=0.00,
            outstanding_amt_local=0.00,
            outstanding_amt=0.00,
        )
        FundsReservationHeaderFactory(
            intervention=self.intervention,
            fr_number=3,
            total_amt=0.00,
            total_amt_local=100.00,
            start_date=datetime.date(2002, 1, 1),
            end_date=datetime.date(2002, 2, 1),
            actual_amt_local=100.00,
            actual_amt=0.00,
            intervention_amt=0.00,
            outstanding_amt_local=0.00,
            outstanding_amt=0.00,
        )
        self.assertTrue(transition_to_closed(self.intervention))
        self.expected["earliest_start_date"] = datetime.date(2000, 1, 1)
        self.expected["latest_end_date"] = datetime.date(2002, 2, 1)
        self.expected["total_actual_amt"] = 300.00
        self.expected["total_frs_amt"] = 300.00
        self.assertFundamentals(self.intervention.total_frs)


class TestTransitionToSigned(BaseTenantTestCase):
    def test_type_status_invalid(self):
        """Certain document types with agreement in certain status
        cannot be signed
        """
        document_type_list = [Intervention.PD, Intervention.SPD]
        status_list = [Agreement.SUSPENDED, Agreement.TERMINATED]
        for s in status_list:
            agreement = AgreementFactory(status=s)
            for d in document_type_list:
                intervention = InterventionFactory(
                    document_type=d,
                    agreement=agreement,
                )
                with self.assertRaisesRegexp(
                        TransitionError,
                        "The PCA related to this record is Draft, Suspended or Terminated."
                ):
                    transition_to_signed(intervention)

    def test_data_processing_agreement_flag_require_attachment(self):
        intervention = InterventionFactory(agreement__status=Agreement.DRAFT,
                                           has_data_processing_agreement=True)
        with self.assertRaisesRegexp(TransitionError, r".* should be provided in attachments."):
            transition_to_signed(intervention)
        InterventionAttachmentFactory(intervention=intervention, type__name=FileType.DATA_PROCESSING_AGREEMENT)
        self.assertTrue(transition_to_signed(intervention))

    def test_activities_involving_children_flag_require_attachment(self):
        intervention = InterventionFactory(agreement__status=Agreement.DRAFT,
                                           has_activities_involving_children=True)
        with self.assertRaisesRegexp(TransitionError, r".* should be provided in attachments."):
            transition_to_signed(intervention)
        InterventionAttachmentFactory(intervention=intervention, type__name=FileType.ACTIVITIES_INVOLVING_CHILDREN)
        self.assertTrue(transition_to_signed(intervention))

    def test_special_conditions_for_construction_flag_require_attachment(self):
        intervention = InterventionFactory(agreement__status=Agreement.DRAFT,
                                           has_special_conditions_for_construction=True)
        with self.assertRaisesRegexp(TransitionError, r".* should be provided in attachments."):
            transition_to_signed(intervention)
        InterventionAttachmentFactory(intervention=intervention,
                                      type__name=FileType.SPECIAL_CONDITIONS_FOR_CONSTRUCTION)
        self.assertTrue(transition_to_signed(intervention))

    def test_valid(self):
        agreement = AgreementFactory(status=Agreement.DRAFT)
        intervention = InterventionFactory(agreement=agreement)
        self.assertTrue(transition_to_signed(intervention))


class TestTransitionToActive(BaseTenantTestCase):
    def test_type_status_invalid(self):
        """Certain document types with agreement not in signed status
        cannot be made active
        """
        document_type_list = [Intervention.PD, Intervention.SPD]
        agreement = AgreementFactory(status=Agreement.DRAFT)
        for d in document_type_list:
            intervention = InterventionFactory(
                document_type=d,
                agreement=agreement,
            )
            with self.assertRaisesRegexp(
                    TransitionError,
                    "PD cannot be activated if"
            ):
                transition_to_active(intervention)

    def test_valid(self):
        agreement = AgreementFactory(status=Agreement.SIGNED)
        intervention = InterventionFactory(agreement=agreement)
        self.assertTrue(transition_to_active(intervention))


class TestTransitionToSuspended(BaseTenantTestCase):
    def test_intervention_suspendable_statuses(self):
        """Interventions in amendment cannot be suspended"""
        suspendable_statuses = [Intervention.SIGNED, Intervention.ACTIVE]

        for suspendable_status in suspendable_statuses:
            intervention = InterventionFactory(
                status=suspendable_status,
            )
            self.assertTrue(transition_to_suspended(intervention))

            InterventionAmendmentFactory(intervention=intervention)
            with self.assertRaises(TransitionError):
                transition_to_suspended(intervention)

    @skip("TODO: enable if the respective transitional validations are implemented")
    def test_intervention_nonsuspendable_statuses(self):
        non_suspendable_statuses = [
            Intervention.DRAFT,
            Intervention.ENDED,
            Intervention.IMPLEMENTED,
            Intervention.CLOSED,
            Intervention.TERMINATED,
        ]

        for non_suspendable_status in non_suspendable_statuses:
            intervention = InterventionFactory(
                status=non_suspendable_status,
            )
            self.assertFalse(transition_to_suspended(intervention))


class TestTransitionToTerminated(BaseTenantTestCase):
    def test_intervention_terminable_statuses(self):
        """Interventions in amendment cannot be terminated"""
        terminable_statuses = [Intervention.SIGNED, Intervention.ACTIVE]
        for terminable_status in terminable_statuses:
            intervention = InterventionFactory(
                status=terminable_status,
                end=datetime.date.today()
            )
            a = AttachmentFactory(code='partners_intervention_termination_doc', content_object=intervention)
            intervention.termination_doc_attachment.add(a)
            self.assertTrue(transition_to_terminated(intervention))

            InterventionAmendmentFactory(intervention=intervention)
            with self.assertRaises(TransitionError):
                transition_to_terminated(intervention)

    @skip("TODO: enable if respective transitional validations are implemented")
    def test_intervention_nonterminable_statuses(self):
        non_terminable_statuses = [
            Intervention.DRAFT,
            Intervention.ENDED,
            Intervention.IMPLEMENTED,
            Intervention.CLOSED,
            Intervention.SUSPENDED,
        ]

        for non_terminable_status in non_terminable_statuses:
            intervention = InterventionFactory(
                status=non_terminable_status,
            )
            self.assertFalse(transition_to_terminated(intervention))


class TestStateDateSignedValid(BaseTenantTestCase):
    def test_start_date_before_signed_date(self):
        """Start date before max signed date is invalid"""
        intervention = InterventionFactory(
            signed_by_unicef_date=datetime.date(2001, 2, 1),
            signed_by_partner_date=datetime.date(2001, 3, 1),
            signed_pd_document="random.pdf",
            start=datetime.date(2001, 1, 1)
        )
        self.assertFalse(start_date_signed_valid(intervention))

    def test_start_date_before_signed_date_attachment(self):
        """Start date before max signed date is invalid"""
        intervention = InterventionFactory(
            signed_by_unicef_date=datetime.date(2001, 2, 1),
            signed_by_partner_date=datetime.date(2001, 3, 1),
            start=datetime.date(2001, 1, 1)
        )
        AttachmentFactory(
            file="random.pdf",
            code="partners_intervention_signed_pd",
            content_object=intervention
        )
        self.assertFalse(start_date_signed_valid(intervention))

    def test_start_date_after_signed_date(self):
        """Start date after max signed date is valid"""
        intervention = InterventionFactory(
            signed_by_unicef_date=datetime.date(2001, 2, 1),
            signed_by_partner_date=datetime.date(2001, 3, 1),
            signed_pd_document="random.pdf",
            start=datetime.date(2001, 4, 1)
        )
        self.assertTrue(start_date_signed_valid(intervention))

    def test_start_date_after_signed_date_attachment(self):
        """Start date after max signed date is valid"""
        intervention = InterventionFactory(
            signed_by_unicef_date=datetime.date(2001, 2, 1),
            signed_by_partner_date=datetime.date(2001, 3, 1),
            start=datetime.date(2001, 4, 1)
        )
        AttachmentFactory(
            file="random.pdf",
            code="partners_intervention_signed_pd",
            content_object=intervention
        )
        self.assertTrue(start_date_signed_valid(intervention))


class TestStateDateRelatedAgreementValid(BaseTenantTestCase):
    def test_start_date_before_agreement_start(self):
        """Start date before agreement start date is invalid
        If not contingency_pd, and certain document_type
        """
        agreement = AgreementFactory(
            start=datetime.date(2002, 1, 1)
        )
        for document_type in [Intervention.PD, Intervention.SPD]:
            intervention = InterventionFactory(
                agreement=agreement,
                signed_pd_document="random.pdf",
                start=datetime.date(2001, 1, 1),
                contingency_pd=False,
                document_type=document_type,
            )
            self.assertFalse(start_date_related_agreement_valid(intervention))

    def test_start_date_before_agreement_start_attachment(self):
        """Start date before agreement start date is invalid
        If not contingency_pd, and certain document_type
        """
        agreement = AgreementFactory(
            start=datetime.date(2002, 1, 1)
        )
        for document_type in [Intervention.PD, Intervention.SPD]:
            intervention = InterventionFactory(
                agreement=agreement,
                start=datetime.date(2001, 1, 1),
                contingency_pd=False,
                document_type=document_type,
            )
            AttachmentFactory(
                file="random.pdf",
                code="partners_intervention_signed_pd",
                content_object=intervention
            )
            self.assertFalse(start_date_related_agreement_valid(intervention))

    def test_start_date_after_signed_date(self):
        """Start date after agreement start date is invalid
        If not contingency_pd, and certain document_type
        """
        agreement = AgreementFactory()
        intervention = InterventionFactory(
            agreement=agreement,
            signed_pd_document="random.pdf",
            start=datetime.date.today() + datetime.timedelta(days=2),
            contingency_pd=False,
            document_type=Intervention.PD,
        )
        self.assertTrue(start_date_related_agreement_valid(intervention))

    def test_start_date_after_signed_date_attachment(self):
        """Start date after agreement start date is invalid
        If not contingency_pd, and certain document_type
        """
        agreement = AgreementFactory()
        intervention = InterventionFactory(
            agreement=agreement,
            start=datetime.date.today() + datetime.timedelta(days=2),
            contingency_pd=False,
            document_type=Intervention.PD,
        )
        AttachmentFactory(
            file="random.pdf",
            code="partners_intervention_signed_pd",
            content_object=intervention
        )
        self.assertTrue(start_date_related_agreement_valid(intervention))


class TestSignedDateValid(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_user = UserFactory()
        cls.partner_user = PartnerStaffFactory()
        cls.future_date = datetime.date.today() + datetime.timedelta(days=2)

    def test_valid(self):
        """Valid if nothing signed"""
        intervention = Intervention()
        self.assertTrue(signed_date_valid(intervention))

    def test_valid_unicef_signed(self):
        """Valid if signed unicef date and unicef signatory
        and date prior to today
        """
        intervention = Intervention(
            signed_by_unicef_date=datetime.date(2001, 1, 1),
            unicef_signatory=self.unicef_user,
        )
        self.assertTrue(signed_date_valid(intervention))

    def test_invalid_unicef_signed(self):
        """invalid if signed unicef date and unicef signatory
        and date after to today
        """
        intervention = Intervention(
            signed_by_unicef_date=self.future_date,
            unicef_signatory=self.unicef_user,
        )
        self.assertFalse(signed_date_valid(intervention))

    def test_valid_partner_signed(self):
        """Valid if signed partner date and partner signatory
        and date prior to today
        """
        intervention = Intervention(
            signed_by_partner_date=datetime.date(2001, 1, 1),
            partner_authorized_officer_signatory=self.partner_user,
        )
        self.assertTrue(signed_date_valid(intervention))

    def test_invalid_partner_signed(self):
        """invalid if signed partner date and partner signatory
        and date after to today
        """
        intervention = Intervention(
            signed_by_partner_date=self.future_date,
            partner_authorized_officer_signatory=self.partner_user,
        )
        self.assertFalse(signed_date_valid(intervention))

    def test_valid_all_signed(self):
        """Valid if both signed unicef/partner date and
        unicef/partner signatory and date prior to today
        """
        intervention = Intervention(
            signed_by_unicef_date=datetime.date(2001, 1, 1),
            unicef_signatory=self.unicef_user,
            signed_by_partner_date=datetime.date(2001, 1, 1),
            partner_authorized_officer_signatory=self.partner_user,
        )
        self.assertTrue(signed_date_valid(intervention))

    def test_invalid_all_signed_unicef_late(self):
        """invalid if both signed unicef/partner date and
        unicef/partner signatory and unicef date after to today
        """
        intervention = Intervention(
            signed_by_unicef_date=self.future_date,
            unicef_signatory=self.unicef_user,
            signed_by_partner_date=datetime.date(2001, 1, 1),
            partner_authorized_officer_signatory=self.partner_user,
        )
        self.assertFalse(signed_date_valid(intervention))

    def test_invalid_all_signed_partner_late(self):
        """invalid if both signed unicef/partner date and
        unicef/partner signatory and partner date after to today
        """
        intervention = Intervention(
            signed_by_unicef_date=datetime.date(2001, 1, 1),
            unicef_signatory=self.unicef_user,
            signed_by_partner_date=self.future_date,
            partner_authorized_officer_signatory=self.partner_user,
        )
        self.assertFalse(signed_date_valid(intervention))

    def test_invalid_all_signed_both_late(self):
        """invalid if both signed unicef/partner date and
        unicef/partner signatory and unicef/partner date after to today
        """
        intervention = Intervention(
            signed_by_unicef_date=self.future_date,
            unicef_signatory=self.unicef_user,
            signed_by_partner_date=self.future_date,
            partner_authorized_officer_signatory=self.partner_user,
        )
        self.assertFalse(signed_date_valid(intervention))


class TestAmendmentsInvalid(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        self.intervention = InterventionFactory(
            status=Intervention.DRAFT,
        )
        self.intervention.old_instance = self.intervention
        self.amendment = InterventionAmendmentFactory(
            intervention=self.intervention,
            signed_date=datetime.date(2001, 1, 1),
            signed_amendment="random.pdf",
        )

    @skip("update teste with new amendment style")
    def test_valid(self):
        pass
        # self.assertTrue(amendments_valid(self.intervention))

    @skip("update testes with new amendment style")
    def test_change_invalid(self):
        """If not active/signed and amendment changes then invalid"""
        self.amendment.signed_date = datetime.date.today()
        self.amendment.save()
        # mock_check = Mock(return_value=False)
        # with patch(
        #         "etools.applications.partners.validation.interventions.check_rigid_related",
        #         mock_check
        # ):
        #    self.assertFalse(amendments_valid(self.intervention))

    @skip("update teste with new amendment style")
    def test_change_active_valid(self):
        """If active and amendment changes then valid"""
        self.intervention.status = Intervention.ACTIVE
        self.amendment.signed_date = datetime.date.today()
        self.amendment.save()
        # self.assertTrue(amendments_valid(self.intervention))

    @skip("update tests with new amendment style")
    def test_change_signed_valid(self):
        """If signed and amendment changes then valid"""
        self.intervention.status = Intervention.SIGNED
        self.amendment.signed_date = datetime.date.today()
        # self.assertTrue(amendments_valid(self.intervention))

    @skip("update tests with new amendment style")
    def test_other_no_description(self):
        """If amendment is type other, and no other description then invalid"""
        self.amendment.types = [InterventionAmendment.OTHER]
        self.amendment.other_description = None
        self.amendment.save()
        self.assertIsNone(self.amendment.other_description)
        # self.assertFalse(amendments_valid(self.intervention))

    @skip("update tests with new amendment style")
    def test_other_with_description(self):
        """If amendment is type other, and no other description then valid"""
        self.amendment.types = [InterventionAmendment.OTHER]
        self.amendment.other_description = "Description"
        self.amendment.save()
        self.assertIsNotNone(self.amendment.other_description)
        # self.assertTrue(amendments_valid(self.intervention))

    @skip("update tests with new amendment style")
    def test_no_signed_date(self):
        """If amendment has no signed date then invalid"""
        self.amendment.signed_date = None
        self.amendment.save()
        # self.assertFalse(amendments_valid(self.intervention))

    @skip("update tests with new amendment style")
    def test_no_signed_amendment(self):
        """If amendment has no signed amendment then invalid"""
        self.amendment.signed_amendment = None
        self.amendment.save()
        # self.assertFalse(amendments_valid(self.intervention))


class TestSSFAgreementHasNoOtherIntervention(BaseTenantTestCase):
    def setUp(self):
        super().setUp()
        self.agreement = AgreementFactory(
            agreement_type=Agreement.SSFA,
        )
        self.intervention = InterventionFactory(
            document_type=Intervention.SSFA,
            agreement=self.agreement,
        )

    def test_valid(self):
        """If document type not SSFA, then valid"""
        self.intervention.document_type = Intervention.PD
        self.assertTrue(
            ssfa_agreement_has_no_other_intervention(self.intervention)
        )

    def test_ssfa_valid(self):
        """If document type SSFA, and agreement type is SSFA ensure
        agreement interventions count is <= 1
        """
        self.assertTrue(
            ssfa_agreement_has_no_other_intervention(self.intervention)
        )

    def test_ssfa_invalid(self):
        """If document type SSFA, and agreement type is SSFA invalid
        if agreement interventions count is > 1
        """
        InterventionFactory(agreement=self.agreement)
        self.assertFalse(
            ssfa_agreement_has_no_other_intervention(self.intervention)
        )

    def test_agreement_not_ssfa(self):
        """If document type SSFA, and agreement is not then invalid"""
        self.agreement.agreement_type = Agreement.MOU
        with self.assertRaisesRegexp(
                BasicValidationError,
                "Agreement selected is not of type SSFA"
        ):
            ssfa_agreement_has_no_other_intervention(self.intervention)


class TestInterventionValid(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.intervention = InterventionFactory()
        cls.intervention.old_instance = cls.intervention
        cls.validator = InterventionValid(
            cls.intervention,
            user=cls.unicef_staff,
            disable_rigid_check=True,
        )
        cls.validator.permissions = cls.validator.get_permissions(
            cls.intervention
        )
        cls.future_date = datetime.date.today() + datetime.timedelta(days=2)

    def test_check_rigid_fields_disabled_rigid_check(self):
        """If disabled rigid check return None"""
        self.assertIsNone(self.validator.check_rigid_fields(self.intervention))

    def test_check_rigid_fields_invalid(self):
        mock_check = Mock(return_value=(False, None))
        validator = InterventionValid(
            self.intervention,
            user=self.unicef_staff,
        )
        validator.permissions = validator.get_permissions(self.intervention)
        with patch(
                "etools.applications.partners.validation.interventions.check_rigid_fields",
                mock_check
        ):
            with self.assertRaisesRegexp(
                    StateValidationError,
                    "Cannot change fields while"
            ):
                validator.check_rigid_fields(self.intervention)

    def test_state_signed_valid_invalid(self):
        """Invalid if unicef budget is 0"""
        self.intervention.total_unicef_budget = 0
        with self.assertRaisesRegexp(StateValidationError, "UNICEF Cash"):
            self.validator.state_signed_valid(self.intervention)

    def test_state_signed_valid(self):
        """Valid if unicef budget is not 0"""
        self.intervention.total_unicef_budget = 10
        self.assertTrue(self.validator.state_signed_valid(self.intervention))

    def test_state_suspended_valid(self):
        self.assertTrue(self.validator.state_suspended_valid(self.intervention))

    def test_state_active_valid_invalid_start(self):
        """Invalid if start is after today"""
        self.intervention.total_unicef_budget = 10
        self.intervention.start = self.future_date
        with self.assertRaisesRegexp(
                StateValidationError,
                "Today is not after the start date"
        ):
            self.validator.state_active_valid(self.intervention)

    def test_state_active_valid_invalid_budget(self):
        """Invalid if unicef budget is 0"""
        self.intervention.total_unicef_budget = 0
        self.intervention.start = datetime.date(2001, 1, 1)
        with self.assertRaisesRegexp(StateValidationError, "UNICEF Cash"):
            self.validator.state_active_valid(self.intervention)

    def test_state_active_valid(self):
        """Valid if unicef budget is not 0 and start is before today"""
        self.intervention.total_unicef_budget = 10
        self.intervention.start = datetime.date(2001, 1, 1)
        self.assertTrue(
            self.validator.state_active_valid(self.intervention)
        )

    def test_state_ended_valid_invalid(self):
        """Invalid if end date is after today"""
        self.intervention.end = self.future_date
        with self.assertRaisesRegexp(
                StateValidationError,
                "Today is not after the end date"
        ):
            self.validator.state_ended_valid(self.intervention)

    def test_state_ended_valid(self):
        """Invalid if end date is after today"""
        self.intervention.end = datetime.date(2001, 1, 1)
        self.assertTrue(self.validator.state_ended_valid(self.intervention))
