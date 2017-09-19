import datetime

import factory
import factory.fuzzy
from django.contrib.auth.models import Group
from factory import fuzzy
from django.db import connection
from django.utils import timezone, six

from EquiTrack.factories import InterventionFactory, ResultFactory, LocationFactory, \
    SectionFactory as SimpleSectionFactory, OfficeFactory as SimpleOfficeFactory
from attachments.tests.factories import AttachmentFactory
from partners.models import InterventionResultLink, InterventionSectorLocationLink
from reports.models import Sector
from tpm.models import TPMPartner, TPMPartnerStaffMember, TPMVisit, TPMActivity, TPMVisitReportRejectComment
from firms.factories import BaseStaffMemberFactory, BaseFirmFactory, UserFactory as SimpleUserFactory


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


class InterventionResultLinkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InterventionResultLink

    cp_output = factory.SubFactory(ResultFactory)


class SectorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Sector

    name = factory.Sequence(lambda n: 'Sector {}'.format(n))


class InterventionSectorLocationLinkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InterventionSectorLocationLink

    sector = factory.SubFactory(SectorFactory)

    @factory.post_generation
    def locations(self, created, extracted, **kwargs):
        if created:
            self.locations.add(*[LocationFactory() for i in range(3)])

        if extracted:
            self.locations.add(*extracted)


class FullInterventionFactory(InterventionFactory):
    result_links = factory.RelatedFactory(InterventionResultLinkFactory, 'intervention')
    sector_locations = factory.RelatedFactory(InterventionSectorLocationLinkFactory, 'intervention')


class SectionFactory(SimpleSectionFactory):
    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        obj = super(SectionFactory, cls)._create(model_class, *args, **kwargs)

        if hasattr(connection.tenant, 'id') and connection.tenant.schema_name != 'public':
            connection.tenant.sections.add(obj)

        return obj


class TPMActivityFactory(factory.DjangoModelFactory):
    class Meta:
        model = TPMActivity

    partnership = factory.SubFactory(FullInterventionFactory)
    implementing_partner = factory.SelfAttribute('partnership.agreement.partner')
    date = fuzzy.FuzzyDate(_FUZZY_START_DATE, _FUZZY_END_DATE)
    section = factory.SubFactory(SectionFactory)

    attachments__count = 0
    report_attachments__count = 0

    @factory.post_generation
    def cp_output(self, create, extracted, **kwargs):
        if create:
            self.cp_output = self.partnership.result_links.first().cp_output

        if extracted:
            self.cp_output = extracted

    @factory.post_generation
    def locations(self, create, extracted, **kwargs):
        if create:
            self.locations.add(*self.partnership.sector_locations.first().locations.all())

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
            AttachmentFactory(code='activity_report', content_object=self)


class InheritedTrait(factory.Trait):
    def __init__(self, *parents, **kwargs):
        overrides = {}

        for parent in parents:
            overrides.update(parent.overrides)

        overrides.update(kwargs)

        super(InheritedTrait, self).__init__(**overrides)


class OfficeFactory(SimpleOfficeFactory):
    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        obj = super(OfficeFactory, cls)._create(model_class, *args, **kwargs)

        if hasattr(connection.tenant, 'id') and connection.tenant.schema_name != 'public':
            connection.tenant.offices.add(obj)

        return obj


class UserFactory(SimpleUserFactory):
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
                if isinstance(group, six.string_types):
                    extracted[i] = Group.objects.get_or_create(name=group)[0]

            self.groups.add(*extracted)

    @factory.post_generation
    def tpm_partner(self, create, extracted, **kwargs):
        if not create:
            return

        if 'Third Party Monitor' not in self.groups.values_list('name', flat=True):
            return

        if not extracted:
            extracted = SimpleTPMPartnerFactory()

        TPMPartnerStaffMemberFactory(tpm_partner=extracted, user=self)


class TPMVisitFactory(factory.DjangoModelFactory):
    class Meta:
        model = TPMVisit

    status = TPMVisit.STATUSES.draft

    tpm_partner = factory.SubFactory(SimpleTPMPartnerFactory)

    unicef_focal_points__count = 0
    offices__count = 0

    tpm_partner_focal_points__count = 0

    tpm_activities__count = 0

    report_reject_comments__count = 0

    class Params:
        draft = factory.Trait()

        assigned = factory.Trait(
            status=TPMVisit.STATUSES.assigned,
            date_of_assigned=factory.LazyFunction(timezone.now),

            unicef_focal_points__count=3,
            offices__count=3,

            tpm_partner_focal_points__count=3,

            tpm_activities__count=3,

            tpm_activities__attachments__count=3,
        )

        cancelled = factory.Trait(
            status=TPMVisit.STATUSES.cancelled,
            date_of_cancelled=factory.LazyFunction(timezone.now),
        )

        tpm_accepted = InheritedTrait(
            assigned,

            status=TPMVisit.STATUSES.tpm_accepted,
            date_of_tpm_accepted=factory.LazyFunction(timezone.now),
        )

        tpm_rejected = InheritedTrait(
            assigned,

            status=TPMVisit.STATUSES.tpm_rejected,
            date_of_tpm_rejected=factory.LazyFunction(timezone.now),

            reject_comment='Just because.',
        )

        tpm_reported = InheritedTrait(
            tpm_accepted,

            status=TPMVisit.STATUSES.tpm_reported,
            date_of_tpm_reported=factory.LazyFunction(timezone.now),

            tpm_activities__report_attachments__count=3,
        )

        tpm_report_rejected = InheritedTrait(
            tpm_reported,

            status=TPMVisit.STATUSES.tpm_report_rejected,
            date_of_tpm_report_rejected=factory.LazyFunction(timezone.now),

            report_reject_comments__count=1,
        )

        unicef_approved = InheritedTrait(
            tpm_reported,

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
    def offices(self, create, extracted, count, **kwargs):
        if not create:
            return

        if extracted is not None:
            self.offices.add(*extracted)
        else:
            self.offices.add(*[OfficeFactory() for i in range(count)])

    @factory.post_generation
    def unicef_focal_points(self, create, extracted, count, **kwargs):
        if not create:
            return

        if extracted is not None:
            self.unicef_focal_points.add(*extracted)
        else:
            self.unicef_focal_points.add(*[UserFactory(unicef_user=True) for i in range(count)])

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
