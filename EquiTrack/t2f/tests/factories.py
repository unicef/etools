from __future__ import unicode_literals

from datetime import datetime, timedelta
import factory
from factory import fuzzy
from pytz import timezone, UTC

from django.conf import settings

from EquiTrack.factories import UserFactory, OfficeFactory, SectionFactory, ResultFactory, LocationFactory,\
    InterventionFactory
from publics.tests.factories import DSARegionFactory, AirlineCompanyFactory, WBSFactory, GrantFactory, FundFactory, \
    CurrencyFactory, ExpenseTypeFactory
from t2f.models import Travel, TravelActivity, IteneraryItem, Expense, Deduction, CostAssignment, Clearances,\
    ActionPoint, make_travel_reference_number, make_action_point_number, ModeOfTravel, \
    TravelType, Invoice, InvoiceItem

TZ = timezone(settings.TIME_ZONE)
_FUZZY_START_DATE = TZ.localize(datetime.now() - timedelta(days=5))
_FUZZY_END_DATE = TZ.localize(datetime.now() + timedelta(days=5))


class TravelActivityFactory(factory.django.DjangoModelFactory):
    travel_type = TravelType.PROGRAMME_MONITORING
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
    departure_date = fuzzy.FuzzyDateTime(start_dt=_FUZZY_START_DATE, end_dt=TZ.localize(datetime.now()))
    arrival_date = fuzzy.FuzzyDateTime(start_dt=TZ.localize(datetime.now()), end_dt=_FUZZY_END_DATE)
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
    currency = factory.SubFactory(CurrencyFactory)
    amount = fuzzy.FuzzyDecimal(1, 10000)
    type = factory.SubFactory(ExpenseTypeFactory)

    class Meta:
        model = Expense


class DeductionFactory(factory.DjangoModelFactory):
    date = fuzzy.FuzzyDateTime(start_dt=_FUZZY_START_DATE, end_dt=_FUZZY_END_DATE)
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
    due_date = fuzzy.FuzzyDateTime(start_dt=_FUZZY_START_DATE, end_dt=TZ.localize(datetime.now()))
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
    start_date = fuzzy.FuzzyDateTime(start_dt=_FUZZY_START_DATE, end_dt=TZ.localize(datetime.now()))
    end_date = fuzzy.FuzzyDateTime(start_dt=TZ.localize(datetime.now()), end_dt=_FUZZY_END_DATE)
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


class InvoiceFactory(factory.DjangoModelFactory):
    travel = factory.SubFactory(TravelFactory)
    business_area = fuzzy.FuzzyText(length=12)
    vendor_number = fuzzy.FuzzyText(length=12)
    currency = factory.SubFactory(CurrencyFactory)
    amount = fuzzy.FuzzyDecimal(0, 1000)
    status = Invoice.PENDING
    messages = []

    class Meta:
        model = Invoice


class InvoiceItemFactory(factory.DjangoModelFactory):
    invoice = factory.SubFactory(InvoiceFactory)
    wbs = factory.SubFactory(WBSFactory)
    grant = factory.SubFactory(GrantFactory)
    fund = factory.SubFactory(FundFactory)
    amount = fuzzy.FuzzyDecimal(0, 250)

    class Meta:
        model = InvoiceItem
