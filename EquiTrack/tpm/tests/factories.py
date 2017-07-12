import datetime

import factory
import factory.fuzzy
from factory import fuzzy

from EquiTrack.factories import InterventionFactory, LocationFactory, PartnerStaffFactory, \
                                ResultFactory
from partners.models import IndicatorReport, InterventionResultLink, InterventionSectorLocationLink
from reports.models import AppliedIndicator, LowerResult, IndicatorBlueprint, Sector
from tpm.models import TPMPartner, TPMPartnerStaffMember, TPMVisit, TPMLocation, \
                       TPMActivity, TPMSectorCovered, TPMLowResult
from firms.factories import BaseStaffMemberFactory, BaseFirmFactory


class IndicatorBlueprintFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = IndicatorBlueprint

    name = factory.Sequence(lambda n: 'Indicator Blueprint {}'.format(n))


class LowerResultFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = \
            LowerResult

    name = factory.Sequence(lambda n: 'Lower Result {}'.format(n))
    code = factory.Sequence(lambda n: 'lower_result_{}'.format(n))


class InterventionResultLinkFactory(factory.DjangoModelFactory):
    class Meta:
        model = InterventionResultLink

    cp_output = factory.SubFactory(ResultFactory)


class AppliedIndicatorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AppliedIndicator

    indicator = factory.SubFactory(IndicatorBlueprintFactory)
    lower_result = factory.SubFactory(LowerResultFactory)


class IndicatorReportFactory(factory.DjangoModelFactory):
    class Meta:
        model = IndicatorReport

    indicator = factory.SubFactory(AppliedIndicatorFactory)
    partner_staff_member = factory.SubFactory(PartnerStaffFactory)
    total = fuzzy.FuzzyInteger(0)


class SectorFactory(factory.DjangoModelFactory):
    class Meta:
        model = Sector

    name = factory.Sequence(lambda n: 'Sector {}'.format(n))


class TPMPartnerStaffMemberFactory(BaseStaffMemberFactory):
    class Meta:
        model = TPMPartnerStaffMember

    # tpm_partner = factory.SubFactory(TPMPartnerFactory)


class TPMPartnerFactory(BaseFirmFactory):
    class Meta:
        model = TPMPartner

    staff_members = factory.RelatedFactory(TPMPartnerStaffMemberFactory, 'tpm_partner')


class TPMLocationFactory(factory.DjangoModelFactory):
    start_date = factory.fuzzy.FuzzyDate(
        start_date=datetime.datetime.now().date() - datetime.timedelta(days=10),
        end_date=datetime.datetime.now().date()
    )
    end_date = factory.fuzzy.FuzzyDate(
        start_date=datetime.datetime.now().date(),
        end_date=datetime.datetime.now().date() + datetime.timedelta(days=10)
    )

    class Meta:
        model = TPMLocation

    location = factory.SubFactory(LocationFactory)
    # sectors_covered = []
    type_of_site = 'Test'

    @factory.post_generation
    def sector_locations(self, create, extracted, **kwargs):
        InterventionSectorLocationLink.objects.get(
            intervention=self.tpm_low_result.tpm_sector.tpm_activity.partnership,
            sector=self.tpm_low_result.tpm_sector.sector
        ).locations.add(self.location)


class TPMLowResultFactory(factory.DjangoModelFactory):
    class Meta:
        model = TPMLowResult

    tpm_locations = factory.RelatedFactory(TPMLocationFactory, 'tpm_low_result')
    result = factory.SubFactory(
        InterventionResultLinkFactory,
        intervention=factory.SelfAttribute(
            '..tpm_sector.tpm_activity.partnership'
        )
    )


class TPMSectorCoveredFactory(factory.DjangoModelFactory):
    class Meta:
        model = TPMSectorCovered

    tpm_low_results = factory.RelatedFactory(TPMLowResultFactory, 'tpm_sector')
    sector = factory.SubFactory(SectorFactory)

    @factory.post_generation
    def sector_locations(self, create, extracted, **kwargs):
        InterventionSectorLocationLink.objects.get_or_create(
            intervention=self.tpm_activity.partnership,
            sector=self.sector
        )


class TPMActivityFactory(factory.DjangoModelFactory):
    class Meta:
        model = TPMActivity

    tpm_sectors = factory.RelatedFactory(TPMSectorCoveredFactory, 'tpm_activity')
    partnership = factory.SubFactory(InterventionFactory)


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
