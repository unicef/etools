from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile

from factory import fuzzy

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.funds.tests.factories import FundsReservationHeaderFactory
from etools.applications.partners.models import Intervention
from etools.applications.partners.tests.factories import (
    InterventionBudgetFactory,
    InterventionFactory,
    PartnerFactory,
    PartnerStaffFactory,
)
from etools.applications.reports.tests.factories import CountryProgrammeFactory, OfficeFactory, SectionFactory
from etools.applications.users.tests.factories import UserFactory


class BaseTestCase(BaseTenantTestCase):
    def setUp(self):
        super().setUp()

        self.unicef_user = UserFactory(is_staff=True, groups__data=['UNICEF User'])
        self.partnership_manager = UserFactory(is_staff=True, groups__data=['UNICEF User', 'Partnership Manager'])

        self.partner = PartnerFactory(vendor_number=fuzzy.FuzzyText(length=20).fuzz())
        self.partner_staff_member = UserFactory(is_staff=False, groups__data=[])
        self.partner_staff_member.profile.partner_staff_member = PartnerStaffFactory(
            partner=self.partner, email=self.partner_staff_member.email
        ).id
        self.partner_staff_member.profile.save()

        self.partner_authorized_officer = UserFactory(is_staff=False, groups__data=[])
        partner_authorized_officer_staff = PartnerStaffFactory(
            partner=self.partner, email=self.partner_authorized_officer.email
        )
        self.partner_authorized_officer.profile.partner_staff_member_user = partner_authorized_officer_staff.id
        self.partner_authorized_officer.profile.save()

        self.partner_focal_point = UserFactory(is_staff=False, groups__data=[])
        partner_focal_point_staff = PartnerStaffFactory(
            partner=self.partner, email=self.partner_focal_point.email
        )
        self.partner_focal_point.profile.partner_staff_member = partner_focal_point_staff.id
        self.partner_focal_point.profile.save()

        self.draft_intervention = InterventionFactory(
            agreement__partner=self.partner,
            partner_authorized_officer_signatory=partner_authorized_officer_staff,
            cash_transfer_modalities=[Intervention.CASH_TRANSFER_DIRECT],
        )
        self.draft_intervention.unicef_focal_points.add(UserFactory())
        self.draft_intervention.partner_focal_points.add(partner_focal_point_staff)

        country_programme = CountryProgrammeFactory()
        self.ended_intervention = InterventionFactory(
            agreement__partner=self.partner,
            status=Intervention.ENDED,
            signed_by_partner_date=date(year=1970, month=1, day=1),
            partner_authorized_officer_signatory=partner_authorized_officer_staff,
            signed_by_unicef_date=date(year=1970, month=1, day=1),
            country_programme=country_programme,
            start=date(year=1970, month=2, day=1),
            end=date(year=1970, month=3, day=1),
            agreement__country_programme=country_programme,
            cash_transfer_modalities=[Intervention.CASH_TRANSFER_DIRECT],
        )
        FundsReservationHeaderFactory(intervention=self.ended_intervention)
        InterventionBudgetFactory(intervention=self.ended_intervention, unicef_cash_local=1)
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
