"""
Model factories used for generating models dynamically for tests
"""
from datetime import datetime, timedelta, date
import json

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.auth.models import Group
import factory
from factory import fuzzy

from EquiTrack.tests.mixins import SCHEMA_NAME, TENANT_DOMAIN
from users import models as user_models
from reports import models as report_models
from locations import models as location_models
from partners import models as partner_models
from publics import models as publics_models
from funds import models as funds_models
from notification import models as notification_models
from t2f import models as t2f_models
from workplan import models as workplan_models
from workplan.models import WorkplanProject, CoverPage, CoverPageBudget


class OfficeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = user_models.Office

    name = 'An Office'


class SectionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = user_models.Section

    name = factory.Sequence(lambda n: "section_%d" % n)


class CountryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = user_models.Country
        django_get_or_create = ('schema_name',)

    name = "Test Country"
    schema_name = SCHEMA_NAME
    domain_url = TENANT_DOMAIN


class GroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Group

    name = "Partnership Manager"


class UnicefUserGroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Group

    name = "UNICEF User"


class ProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = user_models.UserProfile

    country = factory.SubFactory(CountryFactory)
    office = factory.SubFactory(OfficeFactory)
    section = factory.SubFactory(SectionFactory)
    job_title = 'Chief Tester'
    phone_number = '0123456789'
    # We pass in profile=None to prevent UserFactory from creating another profile
    # (this disables the RelatedFactory)
    user = factory.SubFactory('EquiTrack.factories.UserFactory', profile=None)


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()

    username = factory.Sequence(lambda n: "user_%d" % n)
    email = factory.Sequence(lambda n: "user{}@example.com".format(n))
    password = factory.PostGenerationMethodCall('set_password', 'test')

    # We pass in 'user' to link the generated Profile to our just-generated User
    # This will call ProfileFactory(user=our_new_user), thus skipping the SubFactory.
    profile = factory.RelatedFactory(ProfileFactory, 'user')

    @classmethod
    def _generate(cls, create, attrs):
        """Override the default _generate() to disable the post-save signal."""

        # Note: If the signal was defined with a dispatch_uid, include that in both calls.
        post_save.disconnect(user_models.UserProfile.create_user_profile, get_user_model())
        user = super(UserFactory, cls)._generate(create, attrs)
        post_save.connect(user_models.UserProfile.create_user_profile, get_user_model())
        return user

    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        group, created = Group.objects.get_or_create(name='UNICEF User')
        self.groups.add(group)


class GatewayTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = location_models.GatewayType

    name = factory.Sequence(lambda n: 'GatewayType {}'.format(n))


class LocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = location_models.Location

    name = factory.Sequence(lambda n: 'Location {}'.format(n))
    gateway = factory.SubFactory(GatewayTypeFactory)
    point = GEOSGeometry("POINT(20 20)")
    p_code = factory.Sequence(lambda n: 'PCODE{}'.format(n))


class CartoDBTableFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = location_models.CartoDBTable

    domain = factory.Sequence(lambda n: 'Domain {}'.format(n))
    api_key = factory.Sequence(lambda n: 'API Key {}'.format(n))
    table_name = factory.Sequence(lambda n: 'table_name_{}'.format(n))
    location_type = factory.SubFactory(GatewayTypeFactory)
    domain = factory.Sequence(lambda n: 'Domain {}'.format(n))


class PartnerStaffFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = partner_models.PartnerStaffMember

    title = 'Jedi Master'
    first_name = 'Mace'
    last_name = 'Windu'
    email = factory.Sequence(lambda n: "mace{}@theforce.org".format(n))


class PartnerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = partner_models.PartnerOrganization

    name = factory.Sequence(lambda n: 'Partner {}'.format(n))
    staff_members = factory.RelatedFactory(PartnerStaffFactory, 'partner')


class CountryProgrammeFactory(factory.DjangoModelFactory):
    class Meta:
        model = report_models.CountryProgramme

    name = factory.Sequence(lambda n: 'Country Programme {}'.format(n))
    wbs = factory.Sequence(lambda n: '0000/A0/{:02d}'.format(n))
    from_date = date(date.today().year, 1, 1)
    to_date = date(date.today().year, 12, 31)


class AgreementFactory(factory.django.DjangoModelFactory):
    '''Factory for Agreements. If the agreement type is PCA (the default), the agreement's end date is set from
    the country_programme so any end date passed to this factory is ignored.
    '''
    class Meta:
        model = partner_models.Agreement

    partner = factory.SubFactory(PartnerFactory)
    agreement_type = u'PCA'
    signed_by_unicef_date = date.today()
    signed_by_partner_date = date.today()
    status = 'signed'
    attached_agreement = factory.django.FileField(filename='test_file.pdf')
    country_programme = factory.SubFactory(CountryProgrammeFactory)


class InterventionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = partner_models.Intervention

    agreement = factory.SubFactory(AgreementFactory)
    title = factory.Sequence(lambda n: 'Intervention Title {}'.format(n))
    submission_date = datetime.today()


class InterventionBudgetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = partner_models.InterventionBudget

    intervention = factory.SubFactory(InterventionFactory)
    unicef_cash = 100001.00
    unicef_cash_local = 10.00
    partner_contribution = 200.00
    partner_contribution_local = 20.00
    in_kind_amount = 10.00
    in_kind_amount_local = 10.00


class InterventionPlannedVisitsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = partner_models.InterventionPlannedVisits

    intervention = factory.SubFactory(InterventionFactory)


class ResultTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = report_models.ResultType

    name = factory.Sequence(lambda n: 'ResultType {}'.format(n))


class SectorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = report_models.Sector

    name = factory.Sequence(lambda n: 'Sector {}'.format(n))


class ResultFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = report_models.Result

    result_type = factory.SubFactory(ResultTypeFactory)
    name = factory.Sequence(lambda n: 'Result {}'.format(n))
    from_date = date(date.today().year, 1, 1)
    to_date = date(date.today().year, 12, 31)


class LowerResultFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = report_models.LowerResult

    name = factory.Sequence(lambda n: 'Lower Result {}'.format(n))
    code = factory.Sequence(lambda n: 'Lower Result Code {}'.format(n))


class UnitFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = report_models.Unit

    type = factory.Sequence(lambda n: 'Unit {}'.format(n))


class IndicatorBlueprintFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = report_models.IndicatorBlueprint

    name = factory.Sequence(lambda n: 'Indicator Blueprint {}'.format(n))


class IndicatorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = report_models.Indicator

    name = factory.Sequence(lambda n: 'Indicator {}'.format(n))


class GovernmentInterventionFactory(factory.DjangoModelFactory):
    class Meta:
        model = partner_models.GovernmentIntervention

    partner = factory.SubFactory(PartnerFactory)
    country_programme = factory.SubFactory(CountryProgrammeFactory)
    number = 'RefNumber'


class WorkplanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = workplan_models.Workplan

    country_programme = factory.SubFactory(CountryProgrammeFactory)


class LabelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = workplan_models.Label

    name = factory.Sequence(lambda n: 'Label {}'.format(n))


class ResultWorkplanPropertyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = workplan_models.ResultWorkplanProperty

    workplan = factory.SubFactory(WorkplanFactory)
    result = factory.SubFactory(ResultFactory)
    assumptions = fuzzy.FuzzyText(length=50)
    status = fuzzy.FuzzyChoice(["On Track", "Constrained", "No Progress", "Target Met"])
    prioritized = fuzzy.FuzzyChoice([False, True])
    metadata = {"metadata1": "foo"}
    other_partners = factory.Sequence(lambda n: 'Other Partners {}'.format(n))
    rr_funds = fuzzy.FuzzyInteger(1000)
    or_funds = fuzzy.FuzzyInteger(1000)
    ore_funds = fuzzy.FuzzyInteger(1000)
    sections = [factory.SubFactory(SectionFactory)]
    geotag = [factory.SubFactory(LocationFactory)]
    partners = [factory.SubFactory(PartnerFactory)]
    responsible_persons = [factory.SubFactory(UserFactory)]
    labels = [factory.SubFactory(LabelFactory)]

    @factory.post_generation
    def sections(self, create, extracted, **kwargs):
        # Handle M2M relationships
        if not create:
            return
        if extracted:
            for section in extracted:
                self.sections.add(section)

    @factory.post_generation
    def geotag(self, create, extracted, **kwargs):
        # Handle M2M relationships
        if not create:
            return
        if extracted:
            for geotag in extracted:
                self.geotag.add(geotag)

    @factory.post_generation
    def partners(self, create, extracted, **kwargs):
        # Handle M2M relationships
        if not create:
            return
        if extracted:
            for partner in extracted:
                self.partners.add(partner)

    @factory.post_generation
    def responsible_persons(self, create, extracted, **kwargs):
        # Handle M2M relationships
        if not create:
            return
        if extracted:
            for responsible_person in extracted:
                self.responsible_persons.add(responsible_person)

    @factory.post_generation
    def labels(self, create, extracted, **kwargs):
        # Handle M2M relationships
        if not create:
            return
        if extracted:
            for label in extracted:
                self.labels.add(label)


class CoverPageBudgetFactory(factory.DjangoModelFactory):
    class Meta:
        model = CoverPageBudget

    from_date = factory.LazyAttribute(lambda o: date.today())
    to_date = factory.LazyAttribute(lambda o: date.today() + timedelta(days=3))
    total_amount = fuzzy.FuzzyText(length=50)
    funded_amount = fuzzy.FuzzyText(length=50)
    unfunded_amount = fuzzy.FuzzyText(length=50)


class CoverPageFactory(factory.DjangoModelFactory):
    class Meta:
        model = CoverPage

    national_priority = fuzzy.FuzzyText(length=50)
    responsible_government_entity = fuzzy.FuzzyText(length=255)
    planning_assumptions = fuzzy.FuzzyText(length=255)
    budgets = [factory.SubFactory(CoverPageBudgetFactory),
               factory.SubFactory(CoverPageBudgetFactory)]

    @factory.post_generation
    def budgets(self, create, extracted, **kwargs):
        if create and extracted:
            self.budgets.add(*extracted)


class WorkplanProjectFactory(factory.DjangoModelFactory):
    class Meta:
        model = WorkplanProject

    workplan = factory.SubFactory(WorkplanFactory)
    cover_page = factory.RelatedFactory(CoverPageFactory, 'workplan_project')


class DonorFactory(factory.DjangoModelFactory):
    name = fuzzy.FuzzyText(length=45)

    class Meta:
        model = funds_models.Donor


class GrantFactory(factory.DjangoModelFactory):
    donor = factory.SubFactory(DonorFactory)
    name = fuzzy.FuzzyText(length=32)

    class Meta:
        model = funds_models.Grant


class FundsCommitmentItemFactory(factory.DjangoModelFactory):
    fund_commitment = factory.SubFactory('EquiTrack.factories.FundsCommitmentHeaderFactory')
    line_item = fuzzy.FuzzyText(length=5)

    class Meta:
        model = funds_models.FundsCommitmentItem


class FundsReservationHeaderFactory(factory.DjangoModelFactory):
    intervention = factory.SubFactory(InterventionFactory)
    vendor_code = fuzzy.FuzzyText(length=20)
    fr_number = fuzzy.FuzzyText(length=20)
    document_date = date(date.today().year, 1, 1)
    fr_type = fuzzy.FuzzyText(length=20)
    currency = fuzzy.FuzzyText(length=20)
    document_text = fuzzy.FuzzyText(length=20)

    # this is the field required for validation
    intervention_amt = fuzzy.FuzzyDecimal(1, 300)
    # overall_amount
    total_amt = fuzzy.FuzzyDecimal(1, 300)
    actual_amt = fuzzy.FuzzyDecimal(1, 300)
    outstanding_amt = fuzzy.FuzzyDecimal(1, 300)

    start_date = fuzzy.FuzzyDate(date(date.today().year, 1, 1) - timedelta(days=10),
                                 date(date.today().year, 1, 1))
    end_date = fuzzy.FuzzyDate(date(date.today().year + 1, 1, 1),
                               date(date.today().year + 1, 1, 1) + timedelta(days=10))

    class Meta:
        model = funds_models.FundsReservationHeader


class FundsReservationItemFactory(factory.DjangoModelFactory):
    class Meta:
        model = funds_models.FundsReservationItem

    fund_reservation = factory.SubFactory(FundsReservationHeaderFactory)
    line_item = fuzzy.FuzzyText(length=5)


class FundsCommitmentHeaderFactory(factory.DjangoModelFactory):

    class Meta:
        model = funds_models.FundsCommitmentHeader


# Credit goes to http://stackoverflow.com/a/41154232/2363915
class JSONFieldFactory(factory.DictFactory):

    @classmethod
    def _build(cls, model_class, *args, **kwargs):
        if args:
            raise ValueError(
                "DictFactory %r does not support Meta.inline_args.", cls)
        return json.dumps(model_class(**kwargs))


class NotificationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = notification_models.Notification

    type = "Email"
    sender = factory.SubFactory(AgreementFactory)
    template_name = 'trips/trip/TA_request'
    recipients = ['test@test.com', 'test1@test.com', 'test2@test.com']
    template_data = factory.Dict({'url': 'www.unicef.org',
                                  'pa_assistant': 'Test revised',
                                  'owner_name': 'Tester revised'}, dict_factory=JSONFieldFactory)


class AgreementAmendmentFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = partner_models.AgreementAmendment

    number = factory.Sequence(lambda n: '{:05}'.format(n))
    agreement = factory.SubFactory(AgreementFactory)
    types = [partner_models.AgreementAmendment.CLAUSE]


class TravelExpenseTypeFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = publics_models.TravelExpenseType

    title = factory.Sequence(lambda n: 'Travel Expense Type {}'.format(n))
    vendor_number = factory.Sequence(lambda n: 'Vendor Number {}'.format(n))


class CurrencyFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = publics_models.Currency

    name = factory.Sequence(lambda n: 'Currency {}'.format(n))
    code = fuzzy.FuzzyText(length=5, chars='ABCDEFGHIJKLMNOPQRSTUVWYXZ')


class AirlineCompanyFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = publics_models.AirlineCompany

    name = factory.Sequence(lambda n: 'Airline {}'.format(n))
    code = fuzzy.FuzzyInteger(1000)
    iata = fuzzy.FuzzyText(length=3, chars='ABCDEFGHIJKLMNOPQRSTUVWYXZ')
    icao = fuzzy.FuzzyText(length=3, chars='ABCDEFGHIJKLMNOPQRSTUVWYXZ')
    country = 'Somewhere'


class BusinessRegionFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = publics_models.BusinessRegion

    name = factory.Sequence(lambda n: 'Business Region {}'.format(n))
    code = fuzzy.FuzzyText(length=2, chars='ABCDEFGHIJKLMNOPQRSTUVWYXZ')


class BusinessAreaFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = publics_models.BusinessArea

    name = factory.Sequence(lambda n: 'Business Area {}'.format(n))
    code = fuzzy.FuzzyText(length=32, chars='ABCDEFGHIJKLMNOPQRSTUVWYXZ')
    region = factory.SubFactory(BusinessRegionFactory)


class WBSFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = publics_models.WBS

    name = factory.Sequence(lambda n: 'WBS {}'.format(n))
    business_area = factory.SubFactory(BusinessAreaFactory)


class FundFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = publics_models.Fund

    name = factory.Sequence(lambda n: 'Fund {}'.format(n))


class PublicsGrantFactory(factory.django.DjangoModelFactory):
    '''Factory for publics.models.grant, named to avoid collision with funds.models.grant'''

    class Meta:
        model = publics_models.Grant

    name = factory.Sequence(lambda n: 'Grant {}'.format(n))


class PublicsCountryFactory(factory.django.DjangoModelFactory):
    '''Factory for publics.models.grant, named to avoid collision with users.models.grant'''

    class Meta:
        model = publics_models.Country

    name = factory.Sequence(lambda n: 'Country {}'.format(n))
    long_name = factory.Sequence(lambda n: 'The United Lands {}'.format(n))
    currency = factory.SubFactory(CurrencyFactory)


class DSARegionFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = publics_models.DSARegion

    area_name = factory.Sequence(lambda n: 'DSA Region {}'.format(n))
    area_code = fuzzy.FuzzyText(length=2, chars='ABCDEFGHIJKLMNOPQRSTUVWYXZ')
    country = factory.SubFactory(PublicsCountryFactory)


class DSARateFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = publics_models.DSARate

    region = factory.SubFactory(DSARegionFactory)
    effective_from_date = date.today()
    dsa_amount_usd = 1
    dsa_amount_60plus_usd = 1
    dsa_amount_local = 1
    dsa_amount_60plus_local = 1
    room_rate = 10
    finalization_date = date.today()


class FuzzyTravelStatus(factory.fuzzy.BaseFuzzyAttribute):
    def fuzz(self):
        return factory.fuzzy._random.choice(
            [t[0] for t in t2f_models.Travel.CHOICES]
        )


class TravelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = t2f_models.Travel

    status = FuzzyTravelStatus()


class FuzzyTravelType(factory.fuzzy.BaseFuzzyAttribute):
    def fuzz(self):
        return factory.fuzzy._random.choice(
            [t[0] for t in t2f_models.TravelType.CHOICES]
        )


class TravelActivityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = t2f_models.TravelActivity

    travel_type = FuzzyTravelType()
    primary_traveler = factory.SubFactory(UserFactory)

    @factory.post_generation
    def travels(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for travel in extracted:
                self.travels.add(travel)
