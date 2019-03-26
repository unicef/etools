import datetime
import factory
from factory import fuzzy
from unicef_locations.tests.factories import LocationFactory

from etools.applications.partners.tests.factories import InterventionFactory
from etools.applications.publics.tests.factories import (
    PublicsAirlineCompanyFactory,
    PublicsCurrencyFactory,
    PublicsDSARegionFactory,
)
from etools.applications.action_points.tests.factories import ActionPointFactory
from etools.applications.reports.tests.factories import ResultFactory, SectionFactory
from etools.applications.t2f import models
from etools.applications.users.tests.factories import OfficeFactory, UserFactory

_FUZZY_START_DATE = datetime.date(datetime.date.today().year, 1, 1)
_FUZZY_END_DATE = datetime.date(datetime.date.today().year, 12, 31)
_FUZZY_NOW_DATE = datetime.date.today()


class FuzzyTravelType(factory.fuzzy.BaseFuzzyAttribute):
    def fuzz(self):
        return factory.fuzzy._random.choice(
            [t[0] for t in models.TravelType.CHOICES]
        )


class TravelActivityFactory(factory.django.DjangoModelFactory):
    travel_type = models.TravelType.PROGRAMME_MONITORING
    partner = factory.SelfAttribute('partnership.agreement.partner')
    partnership = factory.SubFactory(InterventionFactory)
    result = factory.SubFactory(ResultFactory)
    primary_traveler = factory.SubFactory(UserFactory)
    date = factory.LazyAttribute(lambda o: datetime.date.today())

    class Meta:
        model = models.TravelActivity

    @factory.post_generation
    def populate_locations(self, create, extracted, **kwargs):
        location = LocationFactory()
        self.locations.add(location)

    @factory.post_generation
    def travels(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for travel in extracted:
                self.travels.add(travel)


class ItineraryItemFactory(factory.DjangoModelFactory):
    origin = fuzzy.FuzzyText(length=32)
    destination = fuzzy.FuzzyText(length=32)
    departure_date = fuzzy.FuzzyDate(
        start_date=_FUZZY_START_DATE,
        end_date=_FUZZY_NOW_DATE,
    )
    arrival_date = fuzzy.FuzzyDate(
        start_date=_FUZZY_NOW_DATE,
        end_date=_FUZZY_END_DATE,
    )
    dsa_region = factory.SubFactory(PublicsDSARegionFactory)
    overnight_travel = False
    mode_of_travel = models.ModeOfTravel.BOAT

    @factory.post_generation
    def populate_airlines(self, create, extracted, **kwargs):
        airline = PublicsAirlineCompanyFactory()
        self.airlines.add(airline)

    class Meta:
        model = models.ItineraryItem


class TravelFactory(factory.DjangoModelFactory):
    traveler = factory.SubFactory(UserFactory)
    supervisor = factory.SubFactory(UserFactory)
    office = factory.SubFactory(OfficeFactory)
    section = factory.SubFactory(SectionFactory)
    start_date = fuzzy.FuzzyDate(
        start_date=_FUZZY_START_DATE,
        end_date=_FUZZY_NOW_DATE,
    )
    end_date = fuzzy.FuzzyDate(
        start_date=_FUZZY_NOW_DATE,
        end_date=_FUZZY_END_DATE,
    )
    purpose = factory.Sequence(lambda n: 'Purpose #{}'.format(n))
    international_travel = False
    ta_required = True
    reference_number = factory.Sequence(lambda n: models.make_travel_reference_number())
    currency = factory.SubFactory(PublicsCurrencyFactory)
    mode_of_travel = []

    itinerary = factory.RelatedFactory(ItineraryItemFactory, 'travel')

    @factory.post_generation
    def populate_activities(self, create, extracted, **kwargs):
        ta = TravelActivityFactory(primary_traveler=self.traveler)
        ta.travels.add(self)

    class Meta:
        model = models.Travel


class FuzzyTravelStatus(factory.fuzzy.BaseFuzzyAttribute):
    def fuzz(self):
        return factory.fuzzy._random.choice(
            [t[0] for t in models.Travel.CHOICES]
        )


class TravelAttachmentFactory(factory.DjangoModelFactory):
    travel = factory.SubFactory(TravelFactory)
    type = fuzzy.FuzzyText(length=64)
    name = fuzzy.FuzzyText(length=50)
    file = factory.django.FileField(filename='test_file.pdf')

    class Meta:
        model = models.TravelAttachment


class T2FActionPointFactory(ActionPointFactory):
    class Meta:
        model = models.T2FActionPoint
