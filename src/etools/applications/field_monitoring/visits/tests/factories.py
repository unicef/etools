import factory
from django.utils import timezone
from factory import fuzzy

from etools.applications.field_monitoring.fm_settings.tests.factories import FMMethodTypeFactory, FMMethodFactory, \
    CPOutputConfigFactory, LocationSiteFactory
from etools.applications.field_monitoring.planning.tests.factories import TaskFactory
from etools.applications.field_monitoring.tests.factories import UserFactory
from etools.applications.field_monitoring.visits.models import Visit, VisitTaskLink, VisitMethodType, \
    TaskCheckListItem, VisitCPOutputConfig
from etools.applications.utils.common.tests.factories import InheritedTrait


class VisitFactory(factory.DjangoModelFactory):
    author = factory.SubFactory(UserFactory)
    primary_field_monitor = factory.SubFactory(UserFactory)
    start_date = fuzzy.FuzzyDateTime(
        start_dt=timezone.datetime(timezone.now().year, 1, 1, tzinfo=timezone.now().tzinfo),
        end_dt=timezone.now()
    )
    end_date = fuzzy.FuzzyDateTime(
        start_dt=timezone.now(),
        end_dt=timezone.datetime(timezone.now().year, 12, 31, tzinfo=timezone.now().tzinfo)
    )
    location_site = factory.SubFactory(LocationSiteFactory)
    location = factory.LazyAttribute(lambda o: o.location_site.parent)

    team_members__count = 0
    tasks__count = 0

    class Meta:
        model = Visit

    class Params:
        draft = factory.Trait(
            status=Visit.STATUS_CHOICES.draft
        )

        pre_assigned = InheritedTrait(
            draft,
            team_members__count=3,
            tasks__count=3,
        )

        assigned = InheritedTrait(
            pre_assigned,
            date_assigned=factory.LazyFunction(timezone.now),
            status=Visit.STATUS_CHOICES.assigned
        )

        pre_finalized = InheritedTrait(
            assigned,
        )

        finalized = InheritedTrait(
            pre_finalized,
            date_finalized=factory.LazyFunction(timezone.now),
            status=Visit.STATUS_CHOICES.finalized
        )

        cancelled = InheritedTrait(
            draft,
            date_cancelled=factory.LazyFunction(timezone.now),
            status=Visit.STATUS_CHOICES.cancelled
        )

    @classmethod
    def attributes(cls, create=False, extra=None):
        if extra and 'status' in extra:

            status = extra.pop('status')
            extra[status] = True
        return super().attributes(create, extra)

    @factory.post_generation
    def team_members(self, create, extracted, count, *kwargs):
        if extracted:
            self.team_members.add(*extracted)
        elif create:
            self.team_members.add(*[UserFactory(unicef_user=True) for i in range(count)])

    @factory.post_generation
    def tasks(self, create, extracted, count, *kwargs):
        if extracted:
            for obj in extracted:
                VisitTaskLinkFactory(visit=self, task=obj)
        elif create:
            [VisitTaskLinkFactory(visit=self, task=TaskFactory()) for i in range(count)]


class VisitTaskLinkFactory(factory.DjangoModelFactory):
    visit = factory.SubFactory(VisitFactory)
    task = factory.SubFactory(TaskFactory)

    class Meta:
        model = VisitTaskLink


class TaskCheckListItemFactory(factory.DjangoModelFactory):
    visit_task = factory.SubFactory(VisitTaskLinkFactory)
    parent_slug = factory.fuzzy.FuzzyText()
    question_number = factory.fuzzy.FuzzyText(length=10)
    question_text = factory.fuzzy.FuzzyText()
    specific_details = factory.fuzzy.FuzzyText()

    methods__count = 0

    class Meta:
        model = TaskCheckListItem

    @factory.post_generation
    def methods(self, create, extracted, count, *kwargs):
        if extracted:
            self.methods.add(*extracted)
        elif create:
            self.methods.add(*[FMMethodFactory(is_types_applicable=True) for i in range(count)])


class VisitMethodTypeFactory(factory.DjangoModelFactory):
    method = factory.SubFactory(FMMethodFactory)
    parent_slug = factory.LazyFunction(lambda: FMMethodTypeFactory().slug)
    visit = factory.SubFactory(VisitFactory)
    name = factory.fuzzy.FuzzyText()
    is_recommended = False

    class Meta:
        model = VisitMethodType


class VisitCPOutputConfigFactory(factory.DjangoModelFactory):
    visit_task = factory.SubFactory(VisitTaskLinkFactory)
    parent = factory.SubFactory(CPOutputConfigFactory)

    class Meta:
        model = VisitCPOutputConfig

    @factory.post_generation
    def recommended_method_types(self, create, extracted, **kwargs):
        if extracted:
            self.recommended_method_types.add(*extracted)
        elif create:
            for method_type in self.parent.recommended_method_types.all():
                VisitMethodTypeFactory(
                    method=method_type.method,
                    parent_slug=method_type.slug,
                    visit=self.visit_task.visit,
                    name=method_type.name,
                    is_recommended=True
                )

    @factory.post_generation
    def government_partners(self, create, extracted, **kwargs):
        self.government_partners.add(*self.parent.government_partners.all())
