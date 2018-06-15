# Python imports
import datetime

from rest_framework import serializers

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.partners.models import Agreement, PartnerType
from etools.applications.partners.serializers.agreements_v2 import AgreementCreateUpdateSerializer
from etools.applications.partners.serializers.partner_organization_v2 import PartnerOrganizationDetailSerializer
from etools.applications.partners.tests.factories import (AgreementAmendmentFactory, AgreementFactory,
                                                          InterventionFactory, PartnerFactory, PartnerStaffFactory,
                                                          PlannedEngagementFactory,)
from etools.applications.reports.tests.factories import CountryProgrammeFactory
from etools.applications.users.tests.factories import UserFactory

_ALL_AGREEMENT_TYPES = [agreement_type[0] for agreement_type in Agreement.AGREEMENT_TYPES]


class AgreementCreateUpdateSerializerBase(BaseTenantTestCase):
    '''Base class for testing AgreementCreateUpdateSerializer'''
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

        cls.partner = PartnerFactory(partner_type=PartnerType.CIVIL_SOCIETY_ORGANIZATION)

        cls.today = datetime.date.today()

        # The serializer examines context['request'].user during the course of its operation. If that's not set, the
        # serializer will fail. It doesn't need a real request object, just something with a .user attribute, so
        # that's what I create here.
        class Stub(object):
            pass
        cls.fake_request = Stub()
        cls.fake_request.user = cls.user

    def setUp(self):
        this_year = self.today.year
        self.country_programme = CountryProgrammeFactory(
            from_date=datetime.date(this_year - 1, 1, 1),
            to_date=datetime.date(this_year + 1, 1, 1)
        )

    def assertSimpleExceptionFundamentals(self, context_manager, expected_message):
        """Given the context manager produced by self.assertRaises(), checks the exception it contains for
        the expected message in the correct location.
        """
        exception = context_manager.exception

        self.assertTrue(hasattr(exception, 'detail'))
        self.assertIsInstance(exception.detail, dict)
        # exception.detail should have only one key.
        self.assertEqual(list(exception.detail.keys()), ['errors'])
        # exception.detail['errors'] should map to a list that contains the expected message.
        self.assertIsInstance(exception.detail['errors'], list)
        self.assertEqual(exception.detail['errors'], [expected_message])

    def assertAmendmentExceptionFundamentals(self, context_manager, expected_message):
        """Given the context manager produced by self.assertRaises() for an amendment-related exception,
        checks the exception it contains for the expected message in the correct location.
        """
        exception = context_manager.exception

        # In this case, exception detail contains a dict that contains a list that contains a dict that contains a list.
        # Example --
        #    {'errors':
        #        [
        #            {'signed_amendment':
        #                [
        #                'Please check that the Document is attached and signatures are not in the future'
        #                ]
        #            }
        #        ]
        #    }
        self.assertTrue(hasattr(exception, 'detail'))
        self.assertIsInstance(exception.detail, dict)
        self.assertEqual(list(exception.detail.keys()), ['errors'])
        self.assertIsInstance(exception.detail['errors'], list)
        self.assertEqual(len(exception.detail['errors']), 1)
        the_error = exception.detail['errors'][0]
        self.assertIsInstance(the_error, dict)
        self.assertEqual(list(the_error.keys()), ['signed_amendment'])
        self.assertIsInstance(the_error['signed_amendment'], list)
        self.assertEqual(the_error['signed_amendment'], [expected_message])


class TestAgreementCreateUpdateSerializer(AgreementCreateUpdateSerializerBase):
    """Exercise the AgreementCreateUpdateSerializer."""

    def test_simple_create(self):
        data = {
            "agreement_type": Agreement.MOU,
            "partner": self.partner.id,
        }
        serializer = AgreementCreateUpdateSerializer(data=data)
        serializer.context['request'] = self.fake_request

        self.assertTrue(serializer.is_valid(raise_exception=True))

    def test_create_fail_country_programme_required_for_PCA(self):
        """Ensure correct error is raised for PCAs with no country programme"""
        data = {
            "agreement_type": Agreement.PCA,
            "partner": self.partner.id,
        }
        serializer = AgreementCreateUpdateSerializer()
        serializer.context['request'] = self.fake_request

        with self.assertRaises(serializers.ValidationError) as context_manager:
            serializer.validate(data=data)

        exception = context_manager.exception

        self.assertIsInstance(exception.detail, dict)
        self.assertEqual(list(exception.detail.keys()), ['country_programme'])
        self.assertEqual(exception.detail['country_programme'], 'Country Programme is required for PCAs!')

    def test_create_fail_one_PCA_per_country_programme_and_partner(self):
        """Ensure correct error is raised for PCAs with duplicate country programme & partner combo"""
        AgreementFactory(
            agreement_type=Agreement.PCA,
            partner=self.partner,
            country_programme=self.country_programme,
        )

        # Create an agreement of exactly the same type.
        data = {
            "agreement_type": Agreement.PCA,
            "partner": self.partner,
            "country_programme": self.country_programme,
        }
        serializer = AgreementCreateUpdateSerializer()
        serializer.context['request'] = self.fake_request

        with self.assertRaises(serializers.ValidationError) as context_manager:
            serializer.validate(data=data)

        self.assertSimpleExceptionFundamentals(
            context_manager,
            'A PCA with this partner already exists for this Country Programme Cycle. '
            'If the record is in "Draft" status please edit that record.'
        )

    def test_create_ok_non_PCA_with_same_programme_and_partner(self):
        """Ensure it is OK to create non-PCA agreements that have the same country programme and partner.

        This is a sibling test to test_create_fail_one_PCA_per_country_programme_and_partner().
        """
        agreement_types = [
            agreement_type for agreement_type in _ALL_AGREEMENT_TYPES if agreement_type != Agreement.PCA]

        for agreement_type in agreement_types:
            AgreementFactory(
                agreement_type=agreement_type,
                partner=self.partner,
                country_programme=self.country_programme,
            )

            # Create an agreement of exactly the same type.
            data = {
                "agreement_type": agreement_type,
                "partner": self.partner.id,
                "country_programme": self.country_programme.id,
            }
            serializer = AgreementCreateUpdateSerializer(data=data)
            serializer.context['request'] = self.fake_request

            self.assertTrue(serializer.is_valid(raise_exception=True))

    def test_create_fail_start_date_after_end_date(self):
        """Ensure create fails if start date is after end date"""
        data = {
            "agreement_type": Agreement.PCA,
            "partner": self.partner,
            "country_programme": self.country_programme,
            "start": self.today + datetime.timedelta(days=5),
            "end": self.today,
        }
        serializer = AgreementCreateUpdateSerializer()
        serializer.context['request'] = self.fake_request

        with self.assertRaises(serializers.ValidationError) as context_manager:
            serializer.validate(data=data)

        self.assertSimpleExceptionFundamentals(
            context_manager,
            'Agreement start date needs to be earlier than or the same as the end date'
        )

    def test_create_ok_with_start_date_equal_end_date(self):
        """Ensure it's OK to create an agreement where the start & end dates are the same."""
        data = {
            "agreement_type": Agreement.PCA,
            "partner": self.partner.id,
            "country_programme": self.country_programme.id,
            "start": self.today,
            "end": self.today,
        }
        serializer = AgreementCreateUpdateSerializer(data=data)
        serializer.context['request'] = self.fake_request

        self.assertTrue(serializer.is_valid(raise_exception=True))

    def test_create_ok_when_start_or_end_not_present(self):
        """Ensure that date validation doesn't kick in when one date or another isn't present"""
        # Test w/start date present but not end date
        data = {
            "agreement_type": Agreement.SSFA,
            "partner": self.partner.id,
            "start": self.today + datetime.timedelta(days=5),
        }
        serializer = AgreementCreateUpdateSerializer(data=data)
        serializer.context['request'] = self.fake_request
        self.assertTrue(serializer.is_valid(raise_exception=True))

        # Test w/end date present but not start date
        data = {
            "agreement_type": Agreement.SSFA,
            "partner": self.partner.id,
            "end": self.today + datetime.timedelta(days=5),
        }
        serializer = AgreementCreateUpdateSerializer(data=data)
        serializer.context['request'] = self.fake_request

        self.assertTrue(serializer.is_valid(raise_exception=True))

    def test_create_with_partner_type(self):
        """Exercise create success & failure related to the rules regarding agreement type and partner type"""
        # Set partner to something other than civil society org.
        self.partner.partner_type = PartnerType.UN_AGENCY
        self.partner.save()

        # Create PCA & SSFA should fail now.
        for agreement_type in (Agreement.PCA, Agreement.SSFA):
            data = {
                "agreement_type": agreement_type,
                "country_programme": self.country_programme,
                "partner": self.partner,
            }
            serializer = AgreementCreateUpdateSerializer(data=data)
            serializer.context['request'] = self.fake_request

            with self.assertRaises(serializers.ValidationError) as context_manager:
                serializer.validate(data=data)

            self.assertSimpleExceptionFundamentals(
                context_manager,
                'Partner type must be CSO for PCA or SSFA agreement types.'
            )

        # Test for all agreement types that are not PCA or SSFA. These should not fail.
        agreement_types = [agreement_type for agreement_type in _ALL_AGREEMENT_TYPES
                           if agreement_type
                           not in (Agreement.PCA, Agreement.SSFA)]

        for agreement_type in agreement_types:
            data = {
                "agreement_type": agreement_type,
                "country_programme": self.country_programme.id,
                "partner": self.partner.id,
            }
            serializer = AgreementCreateUpdateSerializer(data=data)
            serializer.context['request'] = self.fake_request

            self.assertTrue(serializer.is_valid(raise_exception=True))

        # Set partner to civil service org; create all agreement types should succeed
        self.partner.partner_type = PartnerType.CIVIL_SOCIETY_ORGANIZATION
        self.partner.save()

        for agreement_type in _ALL_AGREEMENT_TYPES:
            data = {
                "agreement_type": agreement_type,
                "country_programme": self.country_programme.id,
                "partner": self.partner.id,
            }
            serializer = AgreementCreateUpdateSerializer(data=data)
            serializer.context['request'] = self.fake_request

            self.assertTrue(serializer.is_valid(raise_exception=True))

    def test_create_fail_due_to_signatures_SSFA(self):
        """Ensure signature validation works correctly for SSFA"""
        data = {
            "agreement_type": Agreement.SSFA,
            "partner": self.partner,
            "signed_by_unicef_date": self.today,
        }
        serializer = AgreementCreateUpdateSerializer()
        serializer.context['request'] = self.fake_request

        with self.assertRaises(serializers.ValidationError) as context_manager:
            serializer.validate(data=data)

        self.assertSimpleExceptionFundamentals(
            context_manager,
            'SSFA signatures are captured at the Document (TOR) level, please clear the '
            'signatures and dates and add them to the TOR'
        )

    def test_create_ok_and_fail_due_to_signatures_non_SSFA(self):
        """Ensure signature validation works correctly for non-SSFA types"""
        signatory = UserFactory()
        partner_signatory = PartnerStaffFactory(partner=self.partner)

        # This should succeed; it's OK to have only one set of signatures (UNICEF)
        data = {
            "agreement_type": Agreement.MOU,
            "partner": self.partner.id,
            "signed_by_unicef_date": self.today,
            "signed_by": signatory.id,
        }
        serializer = AgreementCreateUpdateSerializer(data=data)
        serializer.context['request'] = self.fake_request

        self.assertTrue(serializer.is_valid(raise_exception=True))

        # This should succeed; it's OK to have only one set of signatures (partner)
        data = {
            "agreement_type": Agreement.MOU,
            "partner": self.partner.id,
            "signed_by_partner_date": self.today,
            "partner_manager": partner_signatory.id,
        }
        serializer = AgreementCreateUpdateSerializer(data=data)
        serializer.context['request'] = self.fake_request

        self.assertTrue(serializer.is_valid(raise_exception=True))

        # This should succeed; it's OK to have both sets of signatures (UNICEF & partner)
        data = {
            "agreement_type": Agreement.MOU,
            "partner": self.partner.id,
            "signed_by_unicef_date": self.today,
            "signed_by": signatory.id,
            "signed_by_partner_date": self.today,
            "partner_manager": partner_signatory.id,
        }
        serializer = AgreementCreateUpdateSerializer(data=data)
        serializer.context['request'] = self.fake_request

        self.assertTrue(serializer.is_valid(raise_exception=True))

        # This should fail because signed_by_unicef_date and signed_by are both set, but the signed by date is
        # in the future.
        data = {
            "agreement_type": Agreement.MOU,
            "partner": self.partner,
            "signed_by_unicef_date": self.today + datetime.timedelta(days=5),
            "signed_by": signatory,
        }

        with self.assertRaises(serializers.ValidationError) as context_manager:
            serializer.validate(data=data)

        self.assertSimpleExceptionFundamentals(
            context_manager,
            'None of the signatures can be dated in the future'
        )

        # This should fail because signed_by_partner_date and partner_manager are both set, but the signed by date is
        # in the future.
        data = {
            "agreement_type": Agreement.MOU,
            "partner": self.partner,
            "signed_by_partner_date": self.today + datetime.timedelta(days=5),
            "partner_manager": partner_signatory,
        }

        with self.assertRaises(serializers.ValidationError) as context_manager:
            serializer.validate(data=data)

        self.assertSimpleExceptionFundamentals(
            context_manager,
            'None of the signatures can be dated in the future'
        )

    def test_update_intervention(self):
        """Ensure agreement update fails if intervention dates aren't appropriate.

        I don't think it's possible to supply interventions when creating via the serializer, so this only tests update.
        """
        agreement = AgreementFactory(agreement_type=Agreement.SSFA,
                                     partner=self.partner,
                                     status=Agreement.DRAFT,
                                     start=self.today - datetime.timedelta(days=5),
                                     end=self.today + datetime.timedelta(days=5),
                                     signed_by_unicef_date=None,
                                     signed_by_partner_date=None)
        intervention = InterventionFactory(agreement=agreement)

        # Start w/an invalid intervention.
        data = {
            "agreement": agreement,
            "intervention": intervention,
        }
        serializer = AgreementCreateUpdateSerializer()
        # If I don't set serializer.instance, the validator gets confused. I guess (?) this is ordinarily set by DRF
        # during an update?
        serializer.instance = agreement
        serializer.context['request'] = self.fake_request

        with self.assertRaises(serializers.ValidationError) as context_manager:
            serializer.validate(data=data)

        self.assertSimpleExceptionFundamentals(
            context_manager,
            "Start and end dates don't match the Document's start and end"
        )

        # Set start date and save again; it should still fail because end date isn't set.
        intervention.start = agreement.start
        intervention.save()

        with self.assertRaises(serializers.ValidationError) as context_manager:
            serializer.validate(data=data)

        self.assertSimpleExceptionFundamentals(
            context_manager,
            "Start and end dates don't match the Document's start and end"
        )

        # Set start date and save again; it should still fail because end date doesn't match agreement end date.
        intervention.end = agreement.end + datetime.timedelta(days=100)
        intervention.save()

        with self.assertRaises(serializers.ValidationError) as context_manager:
            serializer.validate(data=data)

        self.assertSimpleExceptionFundamentals(
            context_manager,
            "Start and end dates don't match the Document's start and end"
        )

        # Set start date and save again; it should now succeed.
        intervention.end = agreement.end
        intervention.save()

        # Should not raise an exception
        serializer.validate(data=data)

    def test_update_fail_due_to_uneditable_field(self):
        """Exercise changing a field that can't be changed while the agreement has this status."""
        agreement = AgreementFactory(agreement_type=Agreement.MOU,
                                     status=Agreement.DRAFT,
                                     signed_by_unicef_date=None,
                                     signed_by_partner_date=None)
        data = {
            "agreement": agreement,
            "partner": self.partner,
        }
        serializer = AgreementCreateUpdateSerializer()
        # If I don't set serializer.instance, the validator gets confused. I guess (?) this is ordinarily set by DRF
        # during an update?
        serializer.instance = agreement
        serializer.context['request'] = self.fake_request

        with self.assertRaises(serializers.ValidationError) as context_manager:
            serializer.validate(data=data)

        self.assertSimpleExceptionFundamentals(
            context_manager,
            "Cannot change fields while in draft: partner"
        )

    def test_update_fail_due_to_amendments_unsigned(self):
        """Ensure agreement update fails if amendments aren't signed.

        I don't think it's possible to supply amendments when creating via the serializer, so this only tests update.
        """
        agreement = AgreementFactory(agreement_type=Agreement.MOU,
                                     signed_by_unicef_date=None,
                                     signed_by_partner_date=None)

        amendment = AgreementAmendmentFactory(agreement=agreement)
        data = {
            'agreement': agreement,
            'amendments': [amendment],
        }
        serializer = AgreementCreateUpdateSerializer()
        # If I don't set serializer.instance, the validator gets confused. I guess (?) this is ordinarily set by DRF
        # during an update?
        serializer.instance = agreement
        serializer.context['request'] = self.fake_request

        with self.assertRaises(serializers.ValidationError) as context_manager:
            serializer.validate(data=data)

        self.assertAmendmentExceptionFundamentals(
            context_manager,
            'Please check that the Document is attached and signatures are not in the future'
        )

    def test_update_with_due_to_amendments_signed_date(self):
        """Ensure agreement update fails if amendments don't have a signed_date or if it's in the future,
        and that update succeeds when the amendments signatures meet criteria.

        I don't think it's possible to supply amendments when creating via the serializer, so this only tests update.
        """
        agreement = AgreementFactory(agreement_type=Agreement.MOU,
                                     signed_by_unicef_date=None,
                                     signed_by_partner_date=None)

        amendment = AgreementAmendmentFactory(agreement=agreement)
        # I need to give amendment.signed_amendment a name to exercise the date part of the amendment validator.
        amendment.signed_amendment.name = 'fake_amendment.pdf'
        amendment.save()
        data = {
            'agreement': agreement,
            'amendments': [amendment],
        }
        serializer = AgreementCreateUpdateSerializer()
        # If I don't set serializer.instance, the validator gets confused. I guess (?) this is ordinarily set by DRF
        # during an update?
        serializer.instance = agreement
        serializer.context['request'] = self.fake_request

        with self.assertRaises(serializers.ValidationError) as context_manager:
            serializer.validate(data=data)

        self.assertAmendmentExceptionFundamentals(
            context_manager,
            'Please check that the Document is attached and signatures are not in the future'
        )

        # Set the signed date, but set it to the future which should cause a failure.
        amendment.signed_date = self.today + datetime.timedelta(days=5)
        amendment.save()

        with self.assertRaises(serializers.ValidationError) as context_manager:
            serializer.validate(data=data)

        self.assertAmendmentExceptionFundamentals(
            context_manager,
            'Please check that the Document is attached and signatures are not in the future'
        )

        # Change the amendment so it will pass validation.
        amendment.signed_date = self.today
        amendment.save()

        # Should not raise an error.
        serializer.validate(data=data)


class TestAgreementSerializerTransitions(AgreementCreateUpdateSerializerBase):
    """Exercise the transition validations of AgreementCreateUpdateSerializer."""

    def test_fail_transition_to_signed_start_and_end_dates(self):
        """Exercise transition to signed, and validation related to start and end dates."""
        agreement = AgreementFactory(agreement_type=Agreement.MOU,
                                     status=Agreement.DRAFT,
                                     signed_by_unicef_date=None,
                                     signed_by_partner_date=None)
        data = {
            "agreement": agreement,
            "status": Agreement.SIGNED,
        }
        serializer = AgreementCreateUpdateSerializer()
        # If I don't set serializer.instance, the validator gets confused. I guess (?) this is ordinarily set by DRF
        # during an update?
        serializer.instance = agreement
        serializer.context['request'] = self.fake_request
        # Should fail because start date is empty.
        with self.assertRaises(serializers.ValidationError) as context_manager:
            serializer.validate(data=data)

        self.assertSimpleExceptionFundamentals(
            context_manager,
            'Agreement cannot transition to signed until the start date is less than or equal to today'
        )

        # Populate start date, but with a date that's still invalid (in the future)
        agreement.start = self.today + datetime.timedelta(days=5)
        agreement.save()

        # Should fail because start date is in the future
        with self.assertRaises(serializers.ValidationError) as context_manager:
            serializer.validate(data=data)

        self.assertSimpleExceptionFundamentals(
            context_manager,
            'Agreement cannot transition to signed until the start date is less than or equal to today'
        )

        # Fix problem with start date, now allow blank end date to cause a failure.
        agreement.start = self.today - datetime.timedelta(days=5)
        agreement.save()

        with self.assertRaises(serializers.ValidationError) as context_manager:
            serializer.validate(data=data)

        self.assertSimpleExceptionFundamentals(
            context_manager,
            'Agreement cannot transition to signed unless the end date is defined'
        )

        # Populate end date with a date in the past - should pass validation for MOU's
        agreement.end = self.today - datetime.timedelta(days=3)
        self.assertTrue(serializer.validate(data=data))

        # Fix end date
        agreement.end = self.today
        agreement.save()

        # Should not raise an exception
        serializer.validate(data=data)

    def test_fail_transition_to_ended(self):
        """Exercise transition to ended."""
        # First test valid/positive case
        agreement = AgreementFactory(agreement_type=Agreement.MOU,
                                     status=Agreement.SIGNED,
                                     end=self.today - datetime.timedelta(days=3),
                                     signed_by_unicef_date=None,
                                     signed_by_partner_date=None)
        data = {
            "agreement": agreement,
            "status": Agreement.ENDED,
        }
        serializer = AgreementCreateUpdateSerializer()
        # If I don't set serializer.instance, the validator gets confused. I guess (?) this is ordinarily set by DRF?
        # # during an update?
        serializer.instance = agreement
        serializer.context['request'] = self.fake_request

        # This should succeed
        serializer.validate(data=data)

        # Should fail; no end date set.
        agreement = AgreementFactory(agreement_type=Agreement.MOU,
                                     status=Agreement.SIGNED,
                                     signed_by_unicef_date=None,
                                     signed_by_partner_date=None)
        data = {
            "agreement": agreement,
            "status": Agreement.ENDED,
        }
        serializer = AgreementCreateUpdateSerializer()
        # If I don't set serializer.instance, the validator gets confused. I guess (?) this is ordinarily set by DRF?
        # # during an update?
        serializer.instance = agreement
        serializer.context['request'] = self.fake_request

        with self.assertRaises(serializers.ValidationError) as context_manager:
            serializer.validate(data=data)

        self.assertSimpleExceptionFundamentals(
            context_manager,
            'agreement_transition_to_ended_invalid'
        )

    def test_ensure_field_read_write_status(self):
        """Ensure that the fields I expect to be read-only are read-only; also confirm the converse"""
        expected_read_only_fields = ('id', 'created', 'modified', 'partner_name', 'amendments', 'unicef_signatory',
                                     'partner_signatory', 'agreement_number', 'attached_agreement_file', 'attachment')

        serializer = AgreementCreateUpdateSerializer()

        for field_name, field in serializer.fields.items():
            expected_read_only = (field_name in expected_read_only_fields)
            self.assertEqual(field.read_only, expected_read_only)


class TestPartnerOrganizationDetailSerializer(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

        cls.partner = PartnerFactory(partner_type=PartnerType.CIVIL_SOCIETY_ORGANIZATION)
        cls.engagement = PlannedEngagementFactory(partner=cls.partner)

    def test_retrieve(self):
        serializer = PartnerOrganizationDetailSerializer(instance=self.partner)

        data = serializer.data
        self.assertCountEqual(data.keys(), [
            'address', 'alternate_id', 'alternate_name', 'assessments', 'basis_for_risk_rating', 'blocked', 'city',
            'core_values_assessment', 'core_values_assessment_date', 'core_values_assessment_file', 'country',
            'created', 'cso_type', 'deleted_flag', 'description', 'email', 'hact_min_requirements', 'hact_values',
            'hidden', u'id', 'interventions', 'last_assessment_date', 'modified', 'name', 'net_ct_cy', 'partner_type',
            'phone_number', 'planned_engagement', 'postal_code', 'rating', 'reported_cy', 'shared_with', 'short_name',
            'staff_members', 'street_address', 'total_ct_cp', 'total_ct_cy', 'total_ct_ytd', 'type_of_assessment',
            'vendor_number', 'vision_synced', 'core_values_assessment_attachment', 'planned_visits', 'manually_blocked',
            'flags', 'partner_type_slug'
        ])

        self.assertCountEqual(data['planned_engagement'].keys(), [
            'id', 'scheduled_audit', 'special_audit', 'spot_check_planned_q1', 'spot_check_planned_q2',
            'spot_check_planned_q3', 'spot_check_planned_q4', 'spot_check_follow_up', 'spot_check_required',
            'total_spot_check_planned', 'required_audit'
        ])

        self.assertEquals(len(data['staff_members']), 1)
        self.assertCountEqual(data['staff_members'][0].keys(), [
            'active', 'created', 'email', 'first_name', u'id', 'last_name', 'modified', 'partner', 'phone', 'title'])
