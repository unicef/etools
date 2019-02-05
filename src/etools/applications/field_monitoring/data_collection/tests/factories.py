import factory

from etools.applications.field_monitoring.data_collection.models import StartedMethod, TaskData, CheckListItemValue
from etools.applications.field_monitoring.visits.tests.factories import VisitMethodTypeFactory, VisitFactory, \
    VisitTaskLinkFactory, TaskCheckListItemFactory
from etools.applications.users.tests.factories import UserFactory


class StartedMethodFactory(factory.DjangoModelFactory):
    visit = factory.SubFactory(VisitFactory)
    method = factory.LazyAttribute(lambda o: o.method_type.method)  # todo: allow user data here
    method_type = factory.SubFactory(VisitMethodTypeFactory)
    author = factory.SubFactory(UserFactory)

    class Meta:
        model = StartedMethod

    class Params:
        started = factory.Trait()
        completed = factory.Trait()

    @classmethod
    def attributes(cls, create=False, extra=None):
        if extra and 'status' in extra:

            status = extra.pop('status')
            extra[status] = True
        return super().attributes(create, extra)


class TaskDataFactory(factory.DjangoModelFactory):
    visit_task = factory.SubFactory(VisitTaskLinkFactory, visit__status='assigned')
    started_method = factory.SubFactory(StartedMethodFactory)
    is_probed = True

    class Meta:
        model = TaskData


class CheckListItemValueFactory(factory.DjangoModelFactory):
    task_data = factory.SubFactory(TaskDataFactory)
    checklist_item = factory.SubFactory(TaskCheckListItemFactory)

    class Meta:
        model = CheckListItemValue
