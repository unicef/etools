
from datetime import datetime, timedelta
import factory
from factory import fuzzy
from pytz import UTC

from EquiTrack.factories import UserFactory, OfficeFactory, SectionFactory, ResultFactory, LocationFactory,\
    InterventionFactory
from publics.models import DSARegion, Currency, AirlineCompany, Fund, Grant, WBS, TravelExpenseType, Country,\
    BusinessArea, BusinessRegion
from t2f.models import Travel, TravelActivity, IteneraryItem, Expense, Deduction, CostAssignment, Clearances,\
    ActionPoint, make_travel_reference_number, make_action_point_number, ModeOfTravel, \
    TravelType

_FUZZY_START_DATE = datetime.now() - timedelta(days=5)
_FUZZY_END_DATE = datetime.now() + timedelta(days=5)


class BusinessRegionFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText(length=8)
    code = fuzzy.FuzzyText(length=2)

    class Meta:
        model = BusinessRegion


class BusinessAreaFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText(length=8)
    code = fuzzy.FuzzyText(length=8)
    region = factory.SubFactory(BusinessRegionFactory)

    class Meta:
        model = BusinessArea


class ExpenseTypeFactory(factory.DjangoModelFactory):
    title = fuzzy.FuzzyText(length=12)
    vendor_number = fuzzy.FuzzyText(length=12)

    class Meta:
        model = TravelExpenseType


class WBSFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText(length=12)
    # business_area = factory.SubFactory(BusinessAreaFactory)

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
    code = 'USD'

    class Meta:
        model = Currency


class AirlineCompanyFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText(length=32)
    code = factory.Sequence(lambda n: n)

    class Meta:
        model = AirlineCompany


class CountryFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText(length=32)
    long_name = fuzzy.FuzzyText(length=32)
    iso_2 = fuzzy.FuzzyText(length=2)
    iso_3 = fuzzy.FuzzyText(length=3)
    valid_from = fuzzy.FuzzyDate(_FUZZY_START_DATE.date(), _FUZZY_END_DATE.date())
    valid_to = fuzzy.FuzzyDate(_FUZZY_START_DATE.date(), _FUZZY_END_DATE.date())
    threshold_tae_usd = 0
    threshold_tre_usd = 0

    class Meta:
        model = Country


class DSARegionFactory(factory.DjangoModelFactory):
    country = factory.SubFactory(CountryFactory)
    area_name = fuzzy.FuzzyText(length=32)
    area_code = fuzzy.FuzzyText(length=3)
    dsa_amount_usd = 100
    dsa_amount_60plus_usd = 80
    dsa_amount_local = 200
    dsa_amount_60plus_local = 160
    room_rate = 150
    eff_date = datetime.now().date()
    finalization_date = datetime.now().date()

    class Meta:
        model = DSARegion


class TravelActivityFactory(factory.DjangoModelFactory):
    travel_type = TravelType.ADVOCACY
    partner = factory.SelfAttribute('partnership.agreement.partner')
    partnership = factory.SubFactory(InterventionFactory)
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
    mode_of_travel = ModeOfTravel.BOAT

    @factory.post_generation
    def populate_airlines(self, create, extracted, **kwargs):
        airline = AirlineCompanyFactory()
        self.airlines.add(airline)

    class Meta:
        model = IteneraryItem


class ExpenseFactory(factory.DjangoModelFactory):
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


class ActionPointFactory(factory.DjangoModelFactory):
    action_point_number = factory.Sequence(lambda n: make_action_point_number())
    description = fuzzy.FuzzyText(length=128)
    due_date = fuzzy.FuzzyNaiveDateTime(start_dt=_FUZZY_START_DATE, end_dt=datetime.now())
    person_responsible = factory.SubFactory(UserFactory)
    assigned_by = factory.SubFactory(UserFactory)
    status = 'open'
    created_at = datetime.now(tz=UTC)

    class Meta:
        model = ActionPoint


class TravelFactory(factory.DjangoModelFactory):
    traveler = factory.SubFactory(UserFactory)
    supervisor = factory.SubFactory(UserFactory)
    office = factory.SubFactory(OfficeFactory)
    section = factory.SubFactory(SectionFactory)
    start_date = fuzzy.FuzzyNaiveDateTime(start_dt=_FUZZY_START_DATE, end_dt=datetime.now())
    end_date = fuzzy.FuzzyNaiveDateTime(start_dt=datetime.now(), end_dt=_FUZZY_END_DATE)
    purpose = factory.Sequence(lambda n: 'Purpose #{}'.format(n))
    international_travel = False
    ta_required = True
    reference_number = factory.Sequence(lambda n: make_travel_reference_number())
    currency = factory.SubFactory(CurrencyFactory)
    mode_of_travel = []

    itinerary = factory.RelatedFactory(IteneraryItemFactory, 'travel')
    expenses = factory.RelatedFactory(ExpenseFactory, 'travel')
    deductions = factory.RelatedFactory(DeductionFactory, 'travel')
    cost_assignments = factory.RelatedFactory(CostAssignmentFactory, 'travel')
    clearances = factory.RelatedFactory(ClearanceFactory, 'travel')
    action_points = factory.RelatedFactory(ActionPointFactory, 'travel')

    @factory.post_generation
    def populate_activities(self, create, extracted, **kwargs):
        ta = TravelActivityFactory(primary_traveler=self.traveler)
        ta.travels.add(self)

    class Meta:
        model = Travel
