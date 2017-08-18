import datetime

import factory
import factory.fuzzy
from django.utils import timezone
from factory import fuzzy

from EquiTrack.factories import InterventionFactory, ResultFactory
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


class TPMActivityFactory(factory.DjangoModelFactory):
    class Meta:
        model = TPMActivity

    partnership = factory.SubFactory(InterventionFactory)
    implementing_partner = factory.SelfAttribute('partnership.agreement.partner')
    cp_output = factory.SubFactory(ResultFactory)
    date = fuzzy.FuzzyDate(_FUZZY_START_DATE, _FUZZY_END_DATE)

    @factory.post_generation
    def locations(self, create, extracted, **kwargs):
        if not create:
            return

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
