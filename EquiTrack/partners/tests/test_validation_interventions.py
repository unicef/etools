from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import datetime

from EquiTrack.factories import (
    AgreementFactory,
    FundsReservationHeaderFactory,
    GroupFactory,
    InterventionAttachmentFactory,
    InterventionFactory,
    UserFactory,
)
from EquiTrack.tests.mixins import FastTenantTestCase
from EquiTrack.validation_mixins import TransitionError
from partners.models import Agreement, FileType, Intervention
from partners.validation.interventions import (
    partnership_manager_only,
    start_date_related_agreement_valid,
    start_date_signed_valid,
    transition_ok,
    transition_to_active,
    transition_to_closed,
    transition_to_signed,
)


class TestPartnershipManagerOnly(FastTenantTestCase):
    def test_manager_no_groups(self):
        user = UserFactory()
        with self.assertRaises(TransitionError):
            partnership_manager_only(None, user)

    def test_manager(self):
        user = UserFactory()
        user.groups.add(GroupFactory(name="Partnership Manager"))
        self.assertTrue(partnership_manager_only(None, user))


class TestTransitionOk(FastTenantTestCase):
    def test_ok(self):
        self.assertTrue(transition_ok(None))


class TestTransitionToClosed(FastTenantTestCase):
    def setUp(self):
        super(TestTransitionToClosed, self).setUp()
        self.intervention = InterventionFactory(
            end=datetime.date(2001, 1, 1),
        )
        self.expected = {
            'total_frs_amt': 0,
            'total_outstanding_amt': 0,
            'total_intervention_amt': 0,
            'total_actual_amt': 0,
            'earliest_start_date': None,
            'latest_end_date': None
        }

    def assertFundamentals(self, data):
        for k, v in data.items():
            if k in self.expected.keys():
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
        self.assertFundamentals(intervention.total_frs)

    def test_total_amounts_outstanding_not_zero(self):
        """Total amounts must equal and total outstanding must be zero"""
        frs = FundsReservationHeaderFactory(
            intervention=self.intervention,
            total_amt=0.00,
            intervention_amt=10.00,
            actual_amt=10.00,
            outstanding_amt=5.00
        )
        with self.assertRaisesRegexp(
                TransitionError,
                'Total FR amount needs to equal total actual amount, and '
                'Total Outstanding DCTs need to equal to 0'
        ):
            transition_to_closed(self.intervention)
        self.expected["total_outstanding_amt"] = 5.00
        self.expected["total_intervention_amt"] = 10.00
        self.expected["total_actual_amt"] = 10.00
        self.expected["earliest_start_date"] = frs.start_date
        self.expected["latest_end_date"] = frs.end_date
        self.assertFundamentals(self.intervention.total_frs)

    def test_total_amounts_not_equal(self):
        """Total amounts must equal and total outstanding must be zero"""
        frs = FundsReservationHeaderFactory(
            intervention=self.intervention,
            total_amt=0.00,
            intervention_amt=10.00,
            actual_amt=20.00,
            outstanding_amt=0.00
        )
        with self.assertRaisesRegexp(
                TransitionError,
                'Total FR amount needs to equal total actual amount, and '
                'Total Outstanding DCTs need to equal to 0'
        ):
            transition_to_closed(self.intervention)
        self.expected["total_intervention_amt"] = 10.00
        self.expected["total_actual_amt"] = 20.00
        self.expected["earliest_start_date"] = frs.start_date
        self.expected["latest_end_date"] = frs.end_date
        self.assertFundamentals(self.intervention.total_frs)

    def test_total_amounts_valid(self):
        """Total amounts must equal and total outstanding must be zero"""
        frs = FundsReservationHeaderFactory(
            intervention=self.intervention,
            total_amt=0.00,
            intervention_amt=10.00,
            actual_amt=10.00,
            outstanding_amt=0.00
        )
        self.assertTrue(transition_to_closed(self.intervention))
        self.expected["total_intervention_amt"] = 10.00
        self.expected["total_actual_amt"] = 10.00
        self.expected["earliest_start_date"] = frs.start_date
        self.expected["latest_end_date"] = frs.end_date
        self.assertFundamentals(self.intervention.total_frs)

    def test_attachment_invalid(self):
        """If Total actual amount > 100,000 need attachment with
        type Final Partnership Review
        """
        frs = FundsReservationHeaderFactory(
            intervention=self.intervention,
            total_amt=0.00,
            actual_amt=120000.00,
            intervention_amt=120000.00,
            outstanding_amt=0.00,
        )
        with self.assertRaisesRegexp(
                TransitionError,
                'Total amount transferred greater than 100,000 and no '
                'Final Partnership Review was attached'
        ):
            transition_to_closed(self.intervention)
        self.expected["total_actual_amt"] = 120000.00
        self.expected["total_intervention_amt"] = 120000.00
        self.expected["earliest_start_date"] = frs.start_date
        self.expected["latest_end_date"] = frs.end_date
        self.assertFundamentals(self.intervention.total_frs)

    def test_attachment(self):
        """If Total actual amount > 100,000 need attachment with
        type Final Partnership Review
        """
        file_type = FileType.objects.get(
            name=FileType.FINAL_PARTNERSHIP_REVIEW
        )
        InterventionAttachmentFactory(
            intervention=self.intervention,
            type=file_type
        )
        frs = FundsReservationHeaderFactory(
            intervention=self.intervention,
            total_amt=0.00,
            actual_amt=120000.00,
            intervention_amt=120000.00,
            outstanding_amt=0.00,
        )
        self.assertTrue(transition_to_closed(self.intervention))
        self.expected["total_actual_amt"] = 120000.00
        self.expected["total_intervention_amt"] = 120000.00
        self.expected["earliest_start_date"] = frs.start_date
        self.expected["latest_end_date"] = frs.end_date
        self.assertFundamentals(self.intervention.total_frs)

    def test_total_frs_amount(self):
        """Ensure total_frs_amt set correctly"""
        frs = FundsReservationHeaderFactory(
            intervention=self.intervention,
            total_amt=200.00,
            actual_amt=100.00,
            intervention_amt=100.00,
            outstanding_amt=0.00,
        )
        self.assertTrue(transition_to_closed(self.intervention))
        self.expected["total_frs_amt"] = 200.00
        self.expected["total_actual_amt"] = 100.00
        self.expected["total_intervention_amt"] = 100.00
        self.expected["earliest_start_date"] = frs.start_date
        self.expected["latest_end_date"] = frs.end_date
        self.assertFundamentals(self.intervention.total_frs)

    def test_dates(self):
        """Ensure earliest and latest dates set correctly"""
        FundsReservationHeaderFactory(
            intervention=self.intervention,
            fr_number=1,
            total_amt=0.00,
            start_date=datetime.date(2001, 1, 1),
            end_date=datetime.date(2001, 2, 1),
            actual_amt=100.00,
            intervention_amt=100.00,
            outstanding_amt=0.00,
        )
        FundsReservationHeaderFactory(
            intervention=self.intervention,
            fr_number=2,
            total_amt=0.00,
            start_date=datetime.date(2000, 1, 1),
            end_date=datetime.date(2000, 2, 1),
            actual_amt=100.00,
            intervention_amt=100.00,
            outstanding_amt=0.00,
        )
        FundsReservationHeaderFactory(
            intervention=self.intervention,
            fr_number=3,
            total_amt=0.00,
            start_date=datetime.date(2002, 1, 1),
            end_date=datetime.date(2002, 2, 1),
            actual_amt=100.00,
            intervention_amt=100.00,
            outstanding_amt=0.00,
        )
        self.assertTrue(transition_to_closed(self.intervention))
        self.expected["earliest_start_date"] = datetime.date(2002, 1, 1)
        self.expected["latest_end_date"] = datetime.date(2000, 2, 1)
        self.expected["total_actual_amt"] = 300.00
        self.expected["total_intervention_amt"] = 300.00
        self.assertFundamentals(self.intervention.total_frs)


class TestTransitionToSigned(FastTenantTestCase):
    def test_type_status_invalid(self):
        """Certain document types with agreement in certain status
        cannot be signed
        """
        document_type_list = [Intervention.PD, Intervention.SHPD]
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
                        "The PCA related to this record is Suspended or Terminated."
                ):
                    transition_to_signed(intervention)

    def test_valid(self):
        agreement = AgreementFactory(status=Agreement.DRAFT)
        intervention = InterventionFactory(agreement=agreement)
        self.assertTrue(transition_to_signed(intervention))


class TestTransitionToActive(FastTenantTestCase):
    def test_type_status_invalid(self):
        """Certain document types with agreement not in signed status
        cannot be made active
        """
        document_type_list = [Intervention.PD, Intervention.SHPD]
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


class TestStateDateSignedValid(FastTenantTestCase):
    def test_start_date_before_signed_date(self):
        """Start date before max signed date is invalid"""
        intervention = InterventionFactory(
            signed_by_unicef_date=datetime.date(2001, 2, 1),
            signed_by_partner_date=datetime.date(2001, 3, 1),
            signed_pd_document="random.pdf",
            start=datetime.date(2001, 1, 1)
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


class TestStateDateRelatedAgreementValid(FastTenantTestCase):
    def test_start_date_before_agreement_start(self):
        """Start date before agreement start date is invalid
        If not contingency_pd, and certain document_type
        """
        agreement = AgreementFactory(
            start=datetime.date(2002, 1, 1)
        )
        for document_type in [Intervention.PD, Intervention.SHPD]:
            intervention = InterventionFactory(
                agreement=agreement,
                signed_pd_document="random.pdf",
                start=datetime.date(2001, 1, 1),
                contingency_pd=False,
                document_type=document_type,
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
