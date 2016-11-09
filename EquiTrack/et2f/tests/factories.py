
from datetime import datetime, timedelta
import factory
from factory import fuzzy
from pytz import UTC

from EquiTrack.factories import UserFactory, OfficeFactory, SectionFactory, ResultFactory, GrantFactory, \
    PartnerFactory, PartnershipFactory, ResultFactory, LocationFactory
from ..models import Currency, AirlineCompany, Travel, TravelActivity, IteneraryItem, Expense, Deduction,\
    CostAssignment, Clearances

_FUZZY_START_DATE = datetime.now() - timedelta(days=5)
_FUZZY_END_DATE = datetime.now() + timedelta(days=5)


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


class TravelActivityFactory(factory.DjangoModelFactory):
    travel_type = fuzzy.FuzzyText(length=32)
    partner = factory.SubFactory(PartnerFactory)
    partnership = factory.SubFactory(PartnershipFactory)
    result = factory.SubFactory(ResultFactory)
    location = factory.SubFactory(LocationFactory)
    date = factory.LazyAttribute(lambda o: datetime.now().date())

    class Meta:
        model = TravelActivity


class IteneraryItemFactory(factory.DjangoModelFactory):
    origin = fuzzy.FuzzyText(length=32)
    destination = fuzzy.FuzzyText(length=32)
    departure_date = fuzzy.FuzzyNaiveDateTime(start_dt=_FUZZY_START_DATE, end_dt=datetime.now())
    arrival_date = fuzzy.FuzzyNaiveDateTime(start_dt=datetime.now(), end_dt=_FUZZY_END_DATE)
    dsa_region = fuzzy.FuzzyText(length=32)
    overnight_travel = False
    mode_of_travel = fuzzy.FuzzyText(length=32)
    airline = factory.SubFactory(AirlineCompanyFactory)

    class Meta:
        model = IteneraryItem


class ExpenseFactory(factory.DjangoModelFactory):
    type = fuzzy.FuzzyText(length=32)
    document_currency = factory.SubFactory(CurrencyFactory)
    account_currency = factory.SubFactory(CurrencyFactory)
    amount = fuzzy.FuzzyDecimal(1, 10000)

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
    wbs = factory.SubFactory(ResultFactory)
    share = fuzzy.FuzzyInteger(1, 100)
    grant = factory.SubFactory(GrantFactory)

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

    activites = factory.RelatedFactory(TravelActivityFactory, 'travel')
    itinerary = factory.RelatedFactory(IteneraryItemFactory, 'travel')
    expenses = factory.RelatedFactory(ExpenseFactory, 'travel')
    deductions = factory.RelatedFactory(DeductionFactory, 'travel')
    cost_assignments = factory.RelatedFactory(CostAssignmentFactory, 'travel')
    clearances = factory.RelatedFactory(ClearanceFactory, 'travel')

    class Meta:
        model = Travel
