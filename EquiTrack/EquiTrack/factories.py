"""
Model factories used for generating models dynamically for tests
"""
import json

from workplan.models import WorkplanProject, CoverPage, CoverPageBudget
import decimal
from datetime import datetime, timedelta, date
from django.db.models.signals import post_save
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.auth.models import Group

import factory
from factory import fuzzy

from users import models as user_models
from trips import models as trip_models
from funds import models as fund_models
from reports import models as report_models
from locations import models as location_models
from partners import models as partner_models
from funds.models import Grant, Donor
from notification import models as notification_models
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
    schema_name = 'test'
    domain_url = 'tenant.test.com'


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
        model = user_models.User

    username = factory.Sequence(lambda n: "user_%d" % n)
    email = factory.Sequence(lambda n: "user{}@notanemail.com".format(n))
    password = factory.PostGenerationMethodCall('set_password', 'test')

    #group = factory.SubFactory(UnicefUserGroupFactory)
    # We pass in 'user' to link the generated Profile to our just-generated User
    # This will call ProfileFactory(user=our_new_user), thus skipping the SubFactory.
    profile = factory.RelatedFactory(ProfileFactory, 'user')

    @classmethod
    def _generate(cls, create, attrs):
        """Override the default _generate() to disable the post-save signal."""

        # Note: If the signal was defined with a dispatch_uid, include that in both calls.
        post_save.disconnect(user_models.UserProfile.create_user_profile, user_models.User)
        user = super(UserFactory, cls)._generate(create, attrs)
        post_save.connect(user_models.UserProfile.create_user_profile, user_models.User)
        return user

    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        group, created = Group.objects.get_or_create(name='UNICEF User')
        self.groups.add(group)

class TripFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = trip_models.Trip

    owner = factory.SubFactory(UserFactory)
    supervisor = factory.SubFactory(UserFactory)
    from_date = datetime.today().date()
    to_date = from_date + timedelta(days=1)


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
    staff = factory.RelatedFactory(PartnerStaffFactory, 'partner')


class CountryProgrammeFactory(factory.DjangoModelFactory):
    class Meta:
        model = report_models.CountryProgramme

    name = factory.Sequence(lambda n: 'Country Programme {}'.format(n))
    wbs = factory.Sequence(lambda n: 'WBS {}'.format(n))
    from_date = date(date.today().year, 1, 1)
    to_date = date(date.today().year, 12, 31)


class AgreementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = partner_models.Agreement

    partner = factory.SubFactory(PartnerFactory)
    agreement_type = u'PCA'
    signed_by_unicef_date = date.today()
    status = 'active'
    country_programme = factory.SubFactory(CountryProgrammeFactory)



class PartnershipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = partner_models.PCA

    partner = factory.SubFactory(PartnerFactory)
    agreement = factory.SubFactory(AgreementFactory)
    partnership_type = u'PD'
    title = u'To save the galaxy from the Empire'
    initiation_date = datetime.today()


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
    year = '2017'

class ResultTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = report_models.ResultType

    name = factory.Sequence(lambda n: 'ResultType {}'.format(n))


class ResultStructureFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = report_models.ResultStructure

    name = factory.Sequence(lambda n: 'RSSP {}'.format(n))
    from_date = date(date.today().year, 1, 1)
    to_date = date(date.today().year, 12, 31)


class ResultFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = report_models.Result

    result_structure = factory.SubFactory(ResultStructureFactory)
    result_type = factory.SubFactory(ResultTypeFactory)
    name = factory.Sequence(lambda n: 'Result {}'.format(n))
    from_date = date(date.today().year, 1, 1)
    to_date = date(date.today().year, 12, 31)


class GovernmentInterventionFactory(factory.DjangoModelFactory):
    class Meta:
        model = partner_models.GovernmentIntervention

    partner = factory.SubFactory(PartnerFactory)
    country_programme = factory.SubFactory(CountryProgrammeFactory)
    result_structure = factory.SubFactory(ResultStructureFactory)
    number = 'RefNumber'


class WorkplanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = workplan_models.Workplan

    country_programme = factory.SubFactory(CountryProgrammeFactory)


class CommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = workplan_models.Comment

    text = factory.Sequence(lambda n: 'Comment body {}'.format(n))
    workplan = factory.SubFactory(WorkplanFactory)


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

class MilestoneFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = workplan_models.Milestone

    result_wp_property = factory.SubFactory(ResultWorkplanPropertyFactory)
    description = factory.Sequence(lambda n: 'Description {}'.format(n))
    assumptions = factory.Sequence(lambda n: 'Assumptions {}'.format(n))

class CoverPageBudgetFactory(factory.DjangoModelFactory):
    class Meta:
        model = CoverPageBudget

    date = factory.LazyAttribute(lambda o: datetime.now())
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
        model = Donor


class GrantFactory(factory.DjangoModelFactory):
    donor = factory.SubFactory(DonorFactory)
    name = fuzzy.FuzzyText(length=32)

    class Meta:
        model = Grant


# class FundingCommitmentFactory(factory.django.DjangoModelFactory):
#     class Meta:
#         model = partner_models.FundingCommitment
#
#     grant = grant,
#     intervention = factory.SubFactory(PartnershipFactory)
#
#
#     fr_number = models.CharField(max_length=50)
#     wbs = models.CharField(max_length=50)
#     fc_type = models.CharField(max_length=50)

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
    template_data = factory.Dict({'url': 'www.unicef.org', 'pa_assistant': 'Test revised', 'owner_name': 'Tester revised'}, dict_factory=JSONFieldFactory)
