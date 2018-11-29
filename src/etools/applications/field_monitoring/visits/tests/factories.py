import factory
from django.utils import timezone
from factory import fuzzy

from etools.applications.field_monitoring.fm_settings.tests.factories import FMMethodTypeFactory, FMMethodFactory
from etools.applications.field_monitoring.planning.tests.factories import TaskFactory
from etools.applications.field_monitoring.tests.factories import UserFactory
from etools.applications.field_monitoring.visits.models import Visit, UNICEFVisit, VisitTaskLink, VisitMethodType, \
    TaskCheckListItem
from etools.applications.reports.models import ResultType
from etools.applications.reports.tests.factories import ResultFactory
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

    team_members__count = 0
    tasks__count = 0
    method_types__count = 0

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
                VisitTaskLink.objects.create(visit=self, task=obj)
        elif create:
            [VisitTaskLink.objects.create(visit=self, task=TaskFactory()) for i in range(count)]

    @factory.post_generation
    def method_types(self, create, extracted, count, *kwargs):
        if extracted:
            self.method_types.add(*extracted)
        elif create:
            [VisitMethodTypeFactory(visit=self, is_recommended=True) for i in range(count)]


class UNICEFVisitFactory(VisitFactory):
    class Meta:
        model = UNICEFVisit


class TaskCheckListItemFactory(factory.DjangoModelFactory):
    class Meta:
        model = TaskCheckListItem


class VisitMethodTypeFactory(factory.DjangoModelFactory):
    method = factory.SubFactory(FMMethodFactory)
    parent_slug = factory.LazyFunction(lambda: FMMethodTypeFactory().slug)
    visit = factory.SubFactory(VisitFactory)
    cp_output = factory.SubFactory(ResultFactory, result_type__name=ResultType.OUTPUT)
    name = factory.fuzzy.FuzzyText()
    is_recommended = False

    class Meta:
        model = VisitMethodType
