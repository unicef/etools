import datetime

import factory
import factory.fuzzy
from django.utils import timezone
from factory import fuzzy

from EquiTrack.factories import InterventionFactory, ResultFactory, LocationFactory
from partners.models import InterventionResultLink, InterventionSectorLocationLink
from reports.models import Sector
from tpm.models import TPMPartner, TPMPartnerStaffMember, TPMVisit, TPMActivity
from firms.factories import BaseStaffMemberFactory, BaseFirmFactory


_FUZZY_START_DATE = timezone.now().date() - datetime.timedelta(days=5)
_FUZZY_END_DATE = timezone.now().date() + datetime.timedelta(days=5)


class TPMPartnerStaffMemberFactory(BaseStaffMemberFactory):
    class Meta:
        model = TPMPartnerStaffMember


class TPMPartnerFactory(BaseFirmFactory):
    class Meta:
        model = TPMPartner

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


class TPMActivityFactory(factory.DjangoModelFactory):
    class Meta:
        model = TPMActivity

    partnership = factory.SubFactory(FullInterventionFactory)
    implementing_partner = factory.SelfAttribute('partnership.agreement.partner')
    date = fuzzy.FuzzyDate(_FUZZY_START_DATE, _FUZZY_END_DATE)

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


class TPMVisitFactory(factory.DjangoModelFactory):
    class Meta:
        model = TPMVisit

    class Params:
        duration = datetime.timedelta(days=10)

    tpm_activities = factory.RelatedFactory(TPMActivityFactory, 'tpm_visit')

    @factory.post_generation
    def sections(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            self.sections.add(*extracted)
