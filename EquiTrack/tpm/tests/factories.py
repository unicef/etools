import datetime

import factory
import factory.fuzzy

from EquiTrack.factories import InterventionFactory, ResultFactory
from tpm.models import TPMPartner, TPMPartnerStaffMember, TPMVisit, TPMActivity
from firms.factories import BaseStaffMemberFactory, BaseFirmFactory


class TPMPartnerStaffMemberFactory(BaseStaffMemberFactory):
    class Meta:
        model = TPMPartnerStaffMember

    # tpm_partner = factory.SubFactory(TPMPartnerFactory)


class TPMPartnerFactory(BaseFirmFactory):
    class Meta:
        model = TPMPartner

    staff_members = factory.RelatedFactory(TPMPartnerStaffMemberFactory, 'tpm_partner')


class TPMActivityFactory(factory.DjangoModelFactory):
    class Meta:
        model = TPMActivity

    partnership = factory.SubFactory(InterventionFactory)
    cp_output = factory.SubFactory(ResultFactory)

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

    tpm_partner = factory.SubFactory(TPMPartnerFactory)
    tpm_activities = factory.RelatedFactory(TPMActivityFactory, 'tpm_visit')

    @factory.post_generation
    def sections(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            self.sections.add(*extracted)
