import datetime

import factory
import factory.fuzzy
from factory import fuzzy

from EquiTrack.factories import InterventionFactory, LocationFactory, PartnerStaffFactory, \
                                ResultFactory
from partners.models import IndicatorReport, InterventionResultLink, InterventionSectorLocationLink
from reports.models import AppliedIndicator, LowerResult, IndicatorBlueprint, Sector
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
    locations = factory.RelatedFactory(LocationFactory)
    cp_output = factory.SubFactory(ResultFactory)


class TPMVisitFactory(factory.DjangoModelFactory):
    class Meta:
        model = TPMVisit

    class Params:
        duration = datetime.timedelta(days=10)

    tpm_partner = factory.SubFactory(TPMPartnerFactory)
    tpm_activities = factory.RelatedFactory(TPMActivityFactory, 'tpm_visit')

    @factory.post_generation
    def results(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            self.results.add(*extracted)
