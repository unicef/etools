from copy import copy
from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from factory import fuzzy
from unicef_locations.tests.factories import LocationFactory

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.funds.tests.factories import FundsReservationHeaderFactory
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.models import Intervention
from etools.applications.partners.permissions import PARTNERSHIP_MANAGER_GROUP, PRC_SECRETARY, UNICEF_USER
from etools.applications.partners.tests.factories import InterventionFactory, InterventionReviewFactory, PartnerFactory
from etools.applications.reports.tests.factories import (
    CountryProgrammeFactory,
    OfficeFactory,
    ReportingRequirementFactory,
    SectionFactory,
)
from etools.applications.users.tests.factories import UserFactory


class BaseTestCase(BaseTenantTestCase):
    def setUp(self):
        super().setUp()

        self.unicef_user = UserFactory(is_staff=True)
        self.partnership_manager = UserFactory(
            is_staff=True, realms__data=[UNICEF_USER, PARTNERSHIP_MANAGER_GROUP]
        )
        self.prc_secretary = UserFactory(
            is_staff=True, realms__data=[UNICEF_USER, PRC_SECRETARY]
        )
        self.partner = PartnerFactory(
            organization=OrganizationFactory(vendor_number=fuzzy.FuzzyText(length=20).fuzz())
        )
        self.partner_staff_member = UserFactory(
            realms__data=['IP Viewer'], profile__organization=self.partner.organization
        )

        self.partner_authorized_officer = UserFactory(
            realms__data=['IP Viewer'], profile__organization=self.partner.organization
        )

        self.partner_focal_point = UserFactory(
            realms__data=['IP Viewer'], profile__organization=self.partner.organization
        )

        self.draft_intervention = InterventionFactory(
            agreement__partner=self.partner,
            partner_authorized_officer_signatory=self.partner_authorized_officer,
            cash_transfer_modalities=[Intervention.CASH_TRANSFER_DIRECT],
            date_sent_to_partner=date.today(),
        )
        self.draft_intervention.unicef_focal_points.add(UserFactory())
        self.draft_intervention.unicef_focal_points.add(self.partnership_manager)
        self.draft_intervention.partner_focal_points.add(self.partner_focal_point)

        country_programme = CountryProgrammeFactory()
        review_fields = dict(
            agreement__partner=self.partner,
            status=Intervention.REVIEW,
            partner_authorized_officer_signatory=self.partner_authorized_officer,
            country_programme=country_programme,
            start=date(year=1970, month=2, day=1),
            end=date(year=1970, month=3, day=1),
            date_sent_to_partner=date.today(),
            agreement__country_programme=country_programme,
            cash_transfer_modalities=[Intervention.CASH_TRANSFER_DIRECT],
            budget_owner=UserFactory(),
            partner_accepted=True,
            unicef_accepted=True,
        )
        self.review_intervention = InterventionFactory(**review_fields)
        self.review_intervention.flat_locations.add(LocationFactory())
        ReportingRequirementFactory(intervention=self.review_intervention)
        review = InterventionReviewFactory(intervention=self.review_intervention, overall_approval=None)
        review.submitted_date = timezone.now().date()
        review.submitted_by = UserFactory()
        review.review_type = 'prc'
        review.save()
        self.review_intervention.unicef_focal_points.add(self.partnership_manager)
        self.review_intervention.sections.add(SectionFactory())
        self.review_intervention.offices.add(OfficeFactory())
        self.review_intervention.partner_focal_points.add(self.partner_focal_point)

        signature_fields = copy(review_fields)
        signature_fields.update(**dict(
            status=Intervention.SIGNATURE,
            signed_by_partner_date=date(year=1970, month=1, day=1),
            signed_by_unicef_date=date(year=1970, month=1, day=1),
        ))
        self.signature_intervention = InterventionFactory(**signature_fields)
        self.signature_intervention.flat_locations.add(LocationFactory())
        InterventionReviewFactory(intervention=self.signature_intervention)
        ReportingRequirementFactory(intervention=self.signature_intervention)
        FundsReservationHeaderFactory(intervention=self.signature_intervention)
        AttachmentFactory(
            file=SimpleUploadedFile('test.txt', b'test'),
            code='partners_intervention_signed_pd',
            content_object=self.signature_intervention,
        )
        self.signature_intervention.unicef_focal_points.add(self.partnership_manager)
        self.signature_intervention.sections.add(SectionFactory())
        self.signature_intervention.offices.add(OfficeFactory())
        self.signature_intervention.partner_focal_points.add(self.partner_focal_point)
        self.signature_intervention.review.overall_approval = True
        self.signature_intervention.review.save()

        signed_fields = copy(signature_fields)
        signed_fields.update(**dict(
            unicef_signatory=UserFactory(),
            status=Intervention.SIGNED,
        ))
        self.signed_intervention = InterventionFactory(**signed_fields)
        self.signed_intervention.flat_locations.add(LocationFactory())
        InterventionReviewFactory(intervention=self.signed_intervention)
        ReportingRequirementFactory(intervention=self.signed_intervention)
        FundsReservationHeaderFactory(intervention=self.signed_intervention)
        self.signed_intervention.planned_budget.unicef_cash_local = 1
        self.signed_intervention.planned_budget.save()
        self.signed_intervention.review.overall_approval = True
        self.signed_intervention.review.save()
        AttachmentFactory(
            file=SimpleUploadedFile('test.txt', b'test'),
            code='partners_intervention_signed_pd',
            content_object=self.signed_intervention,
        )
        self.signed_intervention.unicef_focal_points.add(self.partnership_manager)
        self.signed_intervention.sections.add(SectionFactory())
        self.signed_intervention.offices.add(OfficeFactory())
        self.signed_intervention.partner_focal_points.add(self.partner_focal_point)

        ended_fields = copy(signature_fields)
        ended_fields.update(**dict(
            unicef_signatory=UserFactory(),
            status=Intervention.ENDED,
        ))
        self.ended_intervention = InterventionFactory(**ended_fields)
        self.ended_intervention.flat_locations.add(LocationFactory())
        ReportingRequirementFactory(intervention=self.ended_intervention)
        FundsReservationHeaderFactory(intervention=self.ended_intervention)
        self.ended_intervention.planned_budget.unicef_cash_local = 1
        self.ended_intervention.planned_budget.save()
        AttachmentFactory(
            file=SimpleUploadedFile('test.txt', b'test'),
            code='partners_intervention_ended_pd',
            content_object=self.ended_intervention,
        )
        AttachmentFactory(
            file=SimpleUploadedFile('test.txt', b'test'),
            code='partners_intervention_signed_pd',
            content_object=self.ended_intervention,
        )
        self.ended_intervention.unicef_focal_points.add(self.partnership_manager)
        self.ended_intervention.sections.add(SectionFactory())
        self.ended_intervention.offices.add(OfficeFactory())
        self.ended_intervention.partner_focal_points.add(self.partner_focal_point)
