from copy import copy
from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile

from factory import fuzzy

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.funds.tests.factories import FundsReservationHeaderFactory
from etools.applications.partners.models import Intervention
from etools.applications.partners.tests.factories import (
    InterventionFactory,
    InterventionReviewFactory,
    PartnerFactory,
    PartnerStaffFactory,
)
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

        self.unicef_user = UserFactory(is_staff=True, groups__data=['UNICEF User'])
        self.partnership_manager = UserFactory(is_staff=True, groups__data=['UNICEF User', 'Partnership Manager'])

        self.partner = PartnerFactory(vendor_number=fuzzy.FuzzyText(length=20).fuzz())
        self.partner_staff_member = UserFactory(is_staff=False, groups__data=[])
        PartnerStaffFactory(
            partner=self.partner, email=self.partner_staff_member.email, user=self.partner_staff_member,
        )

        self.partner_authorized_officer = UserFactory(is_staff=False, groups__data=[])
        partner_authorized_officer_staff = PartnerStaffFactory(
            partner=self.partner, email=self.partner_authorized_officer.email, user=self.partner_authorized_officer
        )

        self.partner_focal_point = UserFactory(is_staff=False, groups__data=[])
        partner_focal_point_staff = PartnerStaffFactory(
            partner=self.partner, email=self.partner_focal_point.email, user=self.partner_focal_point
        )

        self.draft_intervention = InterventionFactory(
            agreement__partner=self.partner,
            partner_authorized_officer_signatory=partner_authorized_officer_staff,
            cash_transfer_modalities=[Intervention.CASH_TRANSFER_DIRECT],
            date_sent_to_partner=date.today(),
        )
        self.draft_intervention.unicef_focal_points.add(UserFactory())
        self.draft_intervention.partner_focal_points.add(partner_focal_point_staff)

        country_programme = CountryProgrammeFactory()
        review_fields = dict(
            agreement__partner=self.partner,
            status=Intervention.REVIEW,
            partner_authorized_officer_signatory=partner_authorized_officer_staff,
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
        ReportingRequirementFactory(intervention=self.review_intervention)
        self.review_intervention.unicef_focal_points.add(UserFactory())
        self.review_intervention.sections.add(SectionFactory())
        self.review_intervention.offices.add(OfficeFactory())
        self.review_intervention.partner_focal_points.add(partner_focal_point_staff)

        signature_fields = copy(review_fields)
        signature_fields.update(**dict(
            status=Intervention.SIGNATURE,
            signed_by_partner_date=date(year=1970, month=1, day=1),
            signed_by_unicef_date=date(year=1970, month=1, day=1),
        ))
        self.signature_intervention = InterventionFactory(**signature_fields)
        InterventionReviewFactory(intervention=self.signature_intervention)
        ReportingRequirementFactory(intervention=self.signature_intervention)
        FundsReservationHeaderFactory(intervention=self.signature_intervention)
        AttachmentFactory(
            file=SimpleUploadedFile('test.txt', b'test'),
            code='partners_intervention_signed_pd',
            content_object=self.signature_intervention,
        )
        self.signature_intervention.unicef_focal_points.add(UserFactory())
        self.signature_intervention.sections.add(SectionFactory())
        self.signature_intervention.offices.add(OfficeFactory())
        self.signature_intervention.partner_focal_points.add(partner_focal_point_staff)

        ended_fields = copy(signature_fields)
        ended_fields.update(**dict(
            status=Intervention.ENDED,
        ))
        self.ended_intervention = InterventionFactory(**ended_fields)
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
        self.ended_intervention.unicef_focal_points.add(UserFactory())
        self.ended_intervention.sections.add(SectionFactory())
        self.ended_intervention.offices.add(OfficeFactory())
        self.ended_intervention.partner_focal_points.add(partner_focal_point_staff)
