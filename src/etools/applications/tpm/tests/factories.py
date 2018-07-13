
import datetime

from django.contrib.auth.models import Group
from django.db import connection
from django.utils import timezone

import factory.fuzzy
from factory import fuzzy

from etools.applications.action_points.tests.factories import ActionPointFactory
from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.firms.tests.factories import BaseFirmFactory, BaseStaffMemberFactory, BaseUserFactory
from etools.applications.locations.tests.factories import LocationFactory
from etools.applications.partners.models import InterventionResultLink, InterventionSectorLocationLink
from etools.applications.partners.tests.factories import InterventionFactory
from etools.applications.reports.tests.factories import ResultFactory, SectionFactory
from etools.applications.tpm.models import TPMActivity, TPMVisit, TPMVisitReportRejectComment
from etools.applications.tpm.tpmpartners.models import TPMPartner, TPMPartnerStaffMember
from etools.applications.users.tests.factories import OfficeFactory as SimpleOfficeFactory
from etools.applications.utils.common.tests.factories import InheritedTrait

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


class InterventionSectionLocationLinkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InterventionSectorLocationLink

    sector = factory.SubFactory(SectionFactory)

    @factory.post_generation
    def locations(self, created, extracted, **kwargs):
        if created:
            self.locations.add(*[LocationFactory() for i in range(3)])

        if extracted:
            self.locations.add(*extracted)


class FullInterventionFactory(InterventionFactory):
    result_links = factory.RelatedFactory(InterventionResultLinkFactory, 'intervention')
    sector_locations = factory.RelatedFactory(InterventionSectionLocationLinkFactory, 'intervention')


class OfficeFactory(SimpleOfficeFactory):
    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        obj = super(OfficeFactory, cls)._create(model_class, *args, **kwargs)

        if hasattr(connection.tenant, 'id') and connection.tenant.schema_name != 'public':
            connection.tenant.offices.add(obj)

        return obj


class TPMActivityFactory(factory.DjangoModelFactory):
    class Meta:
        model = TPMActivity

    intervention = factory.SubFactory(FullInterventionFactory)
    partner = factory.SelfAttribute('intervention.agreement.partner')
    date = fuzzy.FuzzyDate(_FUZZY_START_DATE, _FUZZY_END_DATE)
    section = factory.SubFactory(SectionFactory)

    attachments__count = 0
    report_attachments__count = 0
    unicef_focal_points__count = 0
    offices__count = 0
    action_points__count = 0

    @factory.post_generation
    def unicef_focal_points(self, create, extracted, count, **kwargs):
        if not create:
            return

        if extracted is not None:
            self.unicef_focal_points.add(*extracted)
        else:
            self.unicef_focal_points.add(*[UserFactory(unicef_user=True) for i in range(count)])

    @factory.post_generation
    def offices(self, create, extracted, count, **kwargs):
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
        if create:
            self.locations.add(*self.intervention.sector_locations.first().locations.all())

        if extracted:
            self.locations.add(*extracted)

    @factory.post_generation
    def attachments(self, create, extracted, count, **kwargs):
        if not create:
            return

        for i in range(count):
            AttachmentFactory(code='activity_attachments', content_object=self)

    @factory.post_generation
    def report_attachments(self, create, extracted, count, **kwargs):
        if not create:
            return

        for i in range(count):
            AttachmentFactory(code='activity_report', content_object=self, **kwargs)

    @factory.post_generation
    def action_points(self, create, extracted, count, **kwargs):
        if not create:
            return

        for i in range(count):
            ActionPointFactory(tpm_activity=self, **kwargs)


class UserFactory(BaseUserFactory):
    """
    User factory with ability to quickly assign tpm related groups with special logic for tpm partner.
    """
    class Params:
        unicef_user = factory.Trait(
            groups=['UNICEF User'],
        )

        pme = factory.Trait(
            groups=['UNICEF User', 'PME'],
        )

        tpm = factory.Trait(
            groups=['Third Party Monitor'],
        )

    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted is not None:
            extracted = extracted[:]
            for i, group in enumerate(extracted):
                if isinstance(group, str):
                    extracted[i] = Group.objects.get_or_create(name=group)[0]

            self.groups.add(*extracted)

    @factory.post_generation
    def tpm_partner(self, create, extracted, **kwargs):
        if not create:
            return

        if 'Third Party Monitor' not in self.groups.values_list('name', flat=True):
            return

        if not extracted:
            extracted = TPMPartnerFactory()

        TPMPartnerStaffMemberFactory(tpm_partner=extracted, user=self)


class TPMVisitFactory(factory.DjangoModelFactory):
    class Meta:
        model = TPMVisit

    status = TPMVisit.STATUSES.draft

    author = factory.SubFactory(UserFactory, pme=True)

    tpm_partner = factory.SubFactory(TPMPartnerFactory)

    tpm_partner_focal_points__count = 0

    tpm_activities__count = 0

    report_reject_comments__count = 0

    report_attachments__count = 0

    class Params:
        draft = factory.Trait()

        pre_assigned = factory.Trait(
            tpm_partner_focal_points__count=3,

            tpm_activities__count=3,

            tpm_activities__attachments__count=3,
            tpm_activities__unicef_focal_points__count=3,
            tpm_activities__offices__count=3,
        )

        assigned = InheritedTrait(
            pre_assigned,
            status=TPMVisit.STATUSES.assigned,
            date_of_assigned=factory.LazyFunction(timezone.now),
        )

        cancelled = factory.Trait(
            status=TPMVisit.STATUSES.cancelled,
            date_of_cancelled=factory.LazyFunction(timezone.now),
        )

        pre_tpm_accepted = InheritedTrait(
            assigned,
        )

        tpm_accepted = InheritedTrait(
            pre_tpm_accepted,

            status=TPMVisit.STATUSES.tpm_accepted,
            date_of_tpm_accepted=factory.LazyFunction(timezone.now),
        )

        pre_tpm_rejected = InheritedTrait(
            assigned,

            reject_comment='Just because.',
        )

        tpm_rejected = InheritedTrait(
            pre_tpm_rejected,

            status=TPMVisit.STATUSES.tpm_rejected,
            date_of_tpm_rejected=factory.LazyFunction(timezone.now),
        )

        pre_tpm_reported = InheritedTrait(
            tpm_accepted,

            tpm_activities__report_attachments__count=1,
            tpm_activities__report_attachments__file_type__name='report',
        )

        tpm_reported = InheritedTrait(
            pre_tpm_reported,

            status=TPMVisit.STATUSES.tpm_reported,
            date_of_tpm_reported=factory.LazyFunction(timezone.now),
        )

        pre_tpm_report_rejected = InheritedTrait(
            tpm_reported,

            report_reject_comments__count=1,
        )

        tpm_report_rejected = InheritedTrait(
            pre_tpm_report_rejected,

            status=TPMVisit.STATUSES.tpm_report_rejected,
            date_of_tpm_report_rejected=factory.LazyFunction(timezone.now),
        )

        pre_unicef_approved = InheritedTrait(
            tpm_reported,
        )

        unicef_approved = InheritedTrait(
            pre_unicef_approved,

            status=TPMVisit.STATUSES.unicef_approved,
            date_of_unicef_approved=factory.LazyFunction(timezone.now),
        )

    @classmethod
    def attributes(cls, create=False, extra=None):
        if extra and 'status' in extra:
            status = extra.pop('status')
            extra[status] = True
        return super(TPMVisitFactory, cls).attributes(create, extra)

    @factory.post_generation
    def tpm_partner_focal_points(self, create, extracted, count, **kwargs):
        if not create:
            return

        if extracted is not None:
            self.tpm_partner_focal_points.add(*extracted)
        else:
            self.tpm_partner_focal_points.add(*[TPMPartnerStaffMemberFactory(tpm_partner=self.tpm_partner)
                                                for i in range(count)])

    @factory.post_generation
    def tpm_activities(self, create, extracted, count, **kwargs):
        if not create:
            return

        for i in range(count):
            TPMActivityFactory(tpm_visit=self, **kwargs)

    @factory.post_generation
    def report_reject_comments(self, create, extracted, count, **kwargs):
        if not create:
            return

        for i in range(count):
            TPMVisitReportRejectComment(
                tpm_visit=self,
                reject_reason='Just because.',
            )

    @factory.post_generation
    def report_attachments(self, create, extracted, count, **kwargs):
        if not create:
            return

        for i in range(count):
            AttachmentFactory(code='visit_report', content_object=self, **kwargs)
