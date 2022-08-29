import datetime

from django.db import connection
from django.utils import timezone

import factory.fuzzy
from factory import fuzzy
from unicef_locations.tests.factories import LocationFactory

from etools.applications.action_points.tests.factories import ActionPointFactory
from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.firms.tests.factories import BaseFirmFactory, BaseStaffMemberFactory
from etools.applications.partners.models import InterventionResultLink
from etools.applications.partners.tests.factories import InterventionFactory
from etools.applications.reports.tests.factories import OfficeFactory, ResultFactory, SectionFactory
from etools.applications.tpm.models import TPMActivity, TPMVisit, TPMVisitReportRejectComment
from etools.applications.tpm.tpmpartners.models import TPMPartner, TPMPartnerStaffMember
from etools.applications.users.tests.factories import PMEUserFactory, UserFactory
from etools.libraries.tests.factories import StatusFactoryMetaClass

_FUZZY_START_DATE = timezone.now().date() - datetime.timedelta(days=5)
_FUZZY_END_DATE = timezone.now().date() + datetime.timedelta(days=5)


class TPMPartnerStaffMemberFactory(BaseStaffMemberFactory):
    class Meta:
        model = TPMPartnerStaffMember


class SimpleTPMPartnerFactory(BaseFirmFactory):
    class Meta:
        model = TPMPartner


class TPMPartnerFactory(SimpleTPMPartnerFactory):
    staff_members = factory.RelatedFactory(TPMPartnerStaffMemberFactory, 'tpm_partner')

    @factory.post_generation
    def countries(self, create, extracted, **kwargs):
        if extracted is not None:
            self.countries.add(*extracted)
        else:
            self.countries.add(connection.tenant)


class InterventionResultLinkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InterventionResultLink

    cp_output = factory.SubFactory(ResultFactory)


class FullInterventionFactory(InterventionFactory):
    result_links = factory.RelatedFactory(InterventionResultLinkFactory, 'intervention')


class TPMActivityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TPMActivity

    intervention = factory.SubFactory(FullInterventionFactory)
    partner = factory.SelfAttribute('intervention.agreement.partner')
    date = fuzzy.FuzzyDate(_FUZZY_START_DATE, _FUZZY_END_DATE)
    section = factory.SubFactory(SectionFactory)

    @factory.post_generation
    def unicef_focal_points(self, create, extracted, count=0, **kwargs):
        if not create:
            return

        if extracted is not None:
            self.unicef_focal_points.add(*extracted)
        else:
            self.unicef_focal_points.add(*[UserFactory() for i in range(count)])

    @factory.post_generation
    def offices(self, create, extracted, count=0, **kwargs):
        if not create:
            return

        if extracted is not None:
            self.offices.add(*extracted)
        else:
            self.offices.add(*[OfficeFactory() for i in range(count)])

    @factory.post_generation
    def cp_output(self, create, extracted, **kwargs):
        if create:
            self.cp_output = self.intervention.result_links.first().cp_output

        if extracted:
            self.cp_output = extracted

    @factory.post_generation
    def locations(self, create, extracted, **kwargs):
        location = LocationFactory()
        self.locations.add(location)

    @factory.post_generation
    def attachments(self, create, extracted, count=0, **kwargs):
        if not create:
            return

        for i in range(count):
            AttachmentFactory(code='activity_attachments', content_object=self)

    @factory.post_generation
    def report_attachments(self, create, extracted, count=0, **kwargs):
        if not create:
            return

        for i in range(count):
            AttachmentFactory(code='activity_report', content_object=self, **kwargs)

    @factory.post_generation
    def action_points(self, create, extracted, count=0, **kwargs):
        if not create:
            return

        for i in range(count):
            ActionPointFactory(tpm_activity=self, **kwargs)


class TPMUserFactory(UserFactory):
    realm_set__data = ['Third Party Monitor']

    @factory.post_generation
    def tpm_partner(self, create, extracted, **kwargs):
        if not create:
            return

        if not extracted:
            extracted = TPMPartnerFactory()

        TPMPartnerStaffMemberFactory(tpm_partner=extracted, user=self)


class BaseTPMVisitFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TPMVisit

    status = TPMVisit.STATUSES.draft

    author = factory.SubFactory(PMEUserFactory)

    tpm_partner = factory.SubFactory(TPMPartnerFactory)

    @factory.post_generation
    def tpm_partner_focal_points(self, create, extracted, count=0, **kwargs):
        if not create:
            return

        if extracted is not None:
            self.tpm_partner_focal_points.add(*extracted)
        else:
            self.tpm_partner_focal_points.add(*[TPMPartnerStaffMemberFactory(tpm_partner=self.tpm_partner)
                                                for i in range(count)])

    @factory.post_generation
    def tpm_activities(self, create, extracted, count=0, **kwargs):
        if not create:
            return

        for i in range(count):
            TPMActivityFactory(tpm_visit=self, **kwargs)

    @factory.post_generation
    def report_reject_comments(self, create, extracted, count=0, **kwargs):
        if not create:
            return
        for i in range(count):
            TPMVisitReportRejectComment(
                tpm_visit=self,
                reject_reason='Just because.',
            )

    @factory.post_generation
    def report_attachments(self, create, extracted, count=0, **kwargs):
        if not create:
            return
        for i in range(count):
            AttachmentFactory(code='visit_report', content_object=self, **kwargs)


class PreAssignedTPMVisitFactory(BaseTPMVisitFactory):
    tpm_partner_focal_points__count = 3
    tpm_activities__count = 3
    tpm_activities__attachments__count = 3
    tpm_activities__unicef_focal_points__count = 3
    tpm_activities__offices__count = 3


class AssignedTPMVisitFactory(PreAssignedTPMVisitFactory):
    status = TPMVisit.STATUSES.assigned
    date_of_assigned = factory.LazyFunction(timezone.now)


class CancelledTPMVisitFactory(AssignedTPMVisitFactory):
    status = TPMVisit.STATUSES.cancelled
    date_of_cancelled = factory.LazyFunction(timezone.now)


class PreTPMAcceptedTPMVisitFactory(AssignedTPMVisitFactory):
    pass


class TPMAcceptedTPMVisitFactory(PreTPMAcceptedTPMVisitFactory):
    status = TPMVisit.STATUSES.tpm_accepted
    date_of_tpm_accepted = factory.LazyFunction(timezone.now)


class PreTPMRejectedTPMVisitFactory(AssignedTPMVisitFactory):
    reject_comment = 'Just because.'


class TPMRejectedTPMVisitFactory(PreTPMRejectedTPMVisitFactory):
    status = TPMVisit.STATUSES.tpm_rejected
    date_of_tpm_rejected = factory.LazyFunction(timezone.now)


class PreTPMReportedTPMVisitFactory(TPMAcceptedTPMVisitFactory):
    tpm_activities__report_attachments__count = 1
    tpm_activities__report_attachments__file_type__name = 'report'


class TPMReportedTPMVisitFactory(PreTPMReportedTPMVisitFactory):
    status = TPMVisit.STATUSES.tpm_reported
    date_of_tpm_reported = factory.LazyFunction(timezone.now)


class PreTPMReportRejectedTPMVisitFactory(TPMReportedTPMVisitFactory):
    report_reject_comments__count = 1


class TPMReportRejectedTPMVisitFactory(PreTPMReportRejectedTPMVisitFactory):
    status = TPMVisit.STATUSES.tpm_report_rejected
    date_of_tpm_report_rejected = factory.LazyFunction(timezone.now)


class PreUnicefApprovedTPMVisitFactory(TPMReportedTPMVisitFactory):
    pass


class UnicefApprovedTPMVisitFactory(PreUnicefApprovedTPMVisitFactory):
    status = TPMVisit.STATUSES.unicef_approved
    date_of_unicef_approved = factory.LazyFunction(timezone.now)


class TPMVisitFactory(BaseTPMVisitFactory, metaclass=StatusFactoryMetaClass):
    status_factories = {
        'pre_assigned': PreAssignedTPMVisitFactory,
        'assigned': AssignedTPMVisitFactory,
        'cancelled': CancelledTPMVisitFactory,
        'pre_tpm_accepted': PreTPMAcceptedTPMVisitFactory,
        'tpm_accepted': TPMAcceptedTPMVisitFactory,
        'pre_tpm_rejected': PreTPMRejectedTPMVisitFactory,
        'tpm_rejected': TPMRejectedTPMVisitFactory,
        'pre_tpm_reported': PreTPMReportedTPMVisitFactory,
        'tpm_reported': TPMReportedTPMVisitFactory,
        'pre_tpm_report_rejected': PreTPMReportRejectedTPMVisitFactory,
        'tpm_report_rejected': TPMReportRejectedTPMVisitFactory,
        'pre_unicef_approved': PreUnicefApprovedTPMVisitFactory,
        'unicef_approved': UnicefApprovedTPMVisitFactory,
    }
