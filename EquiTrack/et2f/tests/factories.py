
from datetime import datetime, timedelta
import factory
from factory import fuzzy

from EquiTrack.factories import UserFactory, OfficeFactory, SectionFactory, PartnerFactory,\
    PartnershipFactory, ResultFactory, LocationFactory
from et2f.models import DSARegion, Currency, AirlineCompany, Travel, TravelActivity, IteneraryItem, Expense, Deduction,\
    CostAssignment, Clearances, ExpenseType, Fund, Grant, WBS

_FUZZY_START_DATE = datetime.now() - timedelta(days=5)
_FUZZY_END_DATE = datetime.now() + timedelta(days=5)


class ExpenseTypeFactory(factory.DjangoModelFactory):
    title = fuzzy.FuzzyText(length=12)
    code = fuzzy.FuzzyText(length=12)

    class Meta:
        model = ExpenseType


class WBSFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText(length=12)

    class Meta:
        model = WBS


class GrantFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText(length=12)
    wbs = factory.SubFactory(WBSFactory)

    class Meta:
        model = Grant


class FundFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText(length=12)
    grant = factory.SubFactory(GrantFactory)

    class Meta:
        model = Fund


class CurrencyFactory(factory.DjangoModelFactory):
    name = 'United States Dollar'
    iso_4217 = 'USD'

    class Meta:
        model = Currency


class AirlineCompanyFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText(length=32)
    code = fuzzy.FuzzyText()

    class Meta:
        model = AirlineCompany


class DSARegionFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText(length=32)
    dsa_amount_usd = 100
    dsa_amount_60plus_usd = 80
    dsa_amount_local = 200
    dsa_amount_60plus_local = 160
    room_rate = 150

    class Meta:
        model = DSARegion


class TravelActivityFactory(factory.DjangoModelFactory):
    travel_type = fuzzy.FuzzyText(length=32)
    partner = factory.SubFactory(PartnerFactory)
    partnership = factory.SubFactory(PartnershipFactory)
    result = factory.SubFactory(ResultFactory)
    date = factory.LazyAttribute(lambda o: datetime.now())

    class Meta:
        model = TravelActivity

    @factory.post_generation
    def populate_locations(self, create, extracted, **kwargs):
        location = LocationFactory()
        self.locations.add(location)


class IteneraryItemFactory(factory.DjangoModelFactory):
    origin = fuzzy.FuzzyText(length=32)
    destination = fuzzy.FuzzyText(length=32)
    departure_date = fuzzy.FuzzyNaiveDateTime(start_dt=_FUZZY_START_DATE, end_dt=datetime.now())
    arrival_date = fuzzy.FuzzyNaiveDateTime(start_dt=datetime.now(), end_dt=_FUZZY_END_DATE)
    dsa_region = factory.SubFactory(DSARegionFactory)
    overnight_travel = False
    mode_of_travel = fuzzy.FuzzyText(length=32)

    @factory.post_generation
    def populate_airlines(self, create, extracted, **kwargs):
        airline = AirlineCompanyFactory()
        self.airlines.add(airline)

    class Meta:
        model = IteneraryItem


class ExpenseFactory(factory.DjangoModelFactory):
    type = fuzzy.FuzzyText(length=32)
    document_currency = factory.SubFactory(CurrencyFactory)
    account_currency = factory.SubFactory(CurrencyFactory)
    amount = fuzzy.FuzzyDecimal(1, 10000)
    type = factory.SubFactory(ExpenseTypeFactory)

    class Meta:
        model = Expense


class DeductionFactory(factory.DjangoModelFactory):
    date = fuzzy.FuzzyNaiveDateTime(start_dt=_FUZZY_START_DATE, end_dt=_FUZZY_END_DATE)
    breakfast = False
    lunch = False
    dinner = False
    accomodation = False
    no_dsa = False

    class Meta:
        model = Deduction


class CostAssignmentFactory(factory.DjangoModelFactory):
    wbs = factory.SubFactory(WBSFactory)
    share = fuzzy.FuzzyInteger(1, 100)
    grant = factory.SubFactory(GrantFactory)
    fund = factory.SubFactory(FundFactory)

    class Meta:
        model = CostAssignment


class ClearanceFactory(factory.DjangoModelFactory):
    medical_clearance = True
    security_clearance = True
    security_course = True

    class Meta:
        model = Clearances


class TravelFactory(factory.DjangoModelFactory):
    traveller = factory.SubFactory(UserFactory)
    supervisor = factory.SubFactory(UserFactory)
    office = factory.SubFactory(OfficeFactory)
    section = factory.SubFactory(SectionFactory)
    start_date = fuzzy.FuzzyNaiveDateTime(start_dt=_FUZZY_START_DATE, end_dt=datetime.now())
    end_date = fuzzy.FuzzyNaiveDateTime(start_dt=datetime.now(), end_dt=_FUZZY_END_DATE)
    purpose = factory.Sequence(lambda n: 'Purpose #{}'.format(n))
    international_travel = False
    ta_required = True
    reference_number = fuzzy.FuzzyText()
    currency = factory.SubFactory(CurrencyFactory)

    itinerary = factory.RelatedFactory(IteneraryItemFactory, 'travel')
    expenses = factory.RelatedFactory(ExpenseFactory, 'travel')
    deductions = factory.RelatedFactory(DeductionFactory, 'travel')
    cost_assignments = factory.RelatedFactory(CostAssignmentFactory, 'travel')
    clearances = factory.RelatedFactory(ClearanceFactory, 'travel')

    @factory.post_generation
    def populate_activities(self, create, extracted, **kwargs):
        ta = TravelActivityFactory()
        ta.travels.add(self)

    class Meta:
        model = Travel
