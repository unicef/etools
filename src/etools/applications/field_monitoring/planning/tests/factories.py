from datetime import date, timedelta

import factory
from factory import fuzzy
from unicef_locations.tests.factories import LocationFactory

from etools.applications.action_points.categories.models import Category
from etools.applications.action_points.tests.factories import ActionPointFactory
from etools.applications.field_monitoring.fm_settings.tests.factories import QuestionFactory
from etools.applications.field_monitoring.planning.models import (
    MonitoringActivity,
    MonitoringActivityGroup,
    QuestionTemplate,
    YearPlan,
)
from etools.applications.field_monitoring.tests.factories import UserFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.libraries.tests.factories import StatusFactoryMetaClass


class YearPlanFactory(factory.django.DjangoModelFactory):
    year = date.today().year

    prioritization_criteria = fuzzy.FuzzyText()
    methodology_notes = fuzzy.FuzzyText()
    target_visits = fuzzy.FuzzyInteger(0, 100)
    modalities = fuzzy.FuzzyText()
    partner_engagement = fuzzy.FuzzyText()

    class Meta:
        model = YearPlan
        django_get_or_create = ('year',)


class BaseMonitoringActivityFactory(factory.django.DjangoModelFactory):
    monitor_type = 'staff'
    location = factory.SubFactory(LocationFactory)

    start_date = date.today()
    end_date = date.today() + timedelta(days=30)

    questions__count = 0

    class Meta:
        model = MonitoringActivity

    @factory.post_generation
    def team_members(self, created, extracted, count=0, **kwargs):
        if extracted:
            self.team_members.add(*extracted)
        elif count:
            self.team_members.add(*UserFactory.create_batch(size=count, unicef_user=True))

    @factory.post_generation
    def sections(self, created, extracted, **kwargs):
        if extracted:
            self.sections.add(*extracted)

    @factory.post_generation
    def offices(self, created, extracted, **kwargs):
        if extracted:
            self.offices.add(*extracted)

    @factory.post_generation
    def partners(self, created, extracted, **kwargs):
        if extracted:
            self.partners.add(*extracted)

    @factory.post_generation
    def cp_outputs(self, created, extracted, **kwargs):
        if extracted:
            self.cp_outputs.add(*extracted)

    @factory.post_generation
    def interventions(self, created, extracted, **kwargs):
        if extracted:
            self.interventions.add(*extracted)

    @factory.post_generation
    def questions(self, created, extracted, count=0, **kwargs):
        if count:
            from etools.applications.field_monitoring.data_collection.tests.factories import ActivityQuestionFactory

            ActivityQuestionFactory.create_batch(count, monitoring_activity=self, **kwargs)

    @factory.post_generation
    def overall_findings(self, created, extracted, generated=False, **kwargs):
        if generated:
            self.prepare_activity_overall_findings()
            self.prepare_questions_overall_findings()


class DraftActivityFactory(BaseMonitoringActivityFactory):
    status = MonitoringActivity.STATUSES.draft


class ChecklistActivityFactory(DraftActivityFactory):
    questions__count = 1
    status = MonitoringActivity.STATUSES.checklist


class ReviewActivityFactory(ChecklistActivityFactory):
    status = MonitoringActivity.STATUSES.review
    overall_findings__generated = True


class PreAssignedActivityFactory(ReviewActivityFactory):
    visit_lead = factory.SubFactory(UserFactory, unicef_user=True)
    report_reviewer = factory.SubFactory(UserFactory, unicef_user=True)
    team_members__count = 2


class AssignedActivityFactory(PreAssignedActivityFactory):
    status = MonitoringActivity.STATUSES.assigned


class DataCollectionActivityFactory(AssignedActivityFactory):
    status = MonitoringActivity.STATUSES.data_collection


class ReportFinalizationActivityFactory(DataCollectionActivityFactory):
    status = MonitoringActivity.STATUSES.report_finalization


class SubmittedActivityFactory(ReportFinalizationActivityFactory):
    status = MonitoringActivity.STATUSES.submitted


class CompletedActivityFactory(SubmittedActivityFactory):
    status = MonitoringActivity.STATUSES.completed


class CancelledActivityFactory(DraftActivityFactory):
    status = MonitoringActivity.STATUSES.cancelled


class MonitoringActivityFactory(BaseMonitoringActivityFactory, metaclass=StatusFactoryMetaClass):
    status_factories = {
        'draft': DraftActivityFactory,
        'checklist': ChecklistActivityFactory,
        'review': ReviewActivityFactory,
        'pre_assigned': PreAssignedActivityFactory,
        'assigned': AssignedActivityFactory,
        'data_collection': DataCollectionActivityFactory,
        'report_finalization': ReportFinalizationActivityFactory,
        'submitted': SubmittedActivityFactory,
        'completed': CompletedActivityFactory,
        'cancelled': CancelledActivityFactory,
    }


class QuestionTemplateFactory(factory.django.DjangoModelFactory):
    question = factory.SubFactory(QuestionFactory)
    specific_details = fuzzy.FuzzyText()

    class Meta:
        model = QuestionTemplate


class MonitoringActivityActionPointFactory(ActionPointFactory):
    monitoring_activity = factory.SubFactory(MonitoringActivityFactory, status='completed')
    category__module = Category.MODULE_CHOICES.fm


class MonitoringActivityGroupFactory(factory.django.DjangoModelFactory):
    partner = factory.SubFactory(PartnerFactory)

    class Meta:
        model = MonitoringActivityGroup

    @factory.post_generation
    def monitoring_activities(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for activity in extracted:
                self.monitoring_activities.add(activity)
