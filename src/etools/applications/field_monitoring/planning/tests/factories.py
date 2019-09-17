from datetime import date, timedelta

import factory
from factory import fuzzy
from unicef_locations.tests.factories import LocationFactory

from etools.applications.field_monitoring.fm_settings.tests.factories import QuestionFactory
from etools.applications.field_monitoring.planning.models import MonitoringActivity, QuestionTemplate, YearPlan
from etools.applications.field_monitoring.tests.factories import UserFactory
from etools.applications.users.tests.factories import OfficeFactory
from etools.libraries.tests.factories import StatusFactoryMetaClass


class YearPlanFactory(factory.DjangoModelFactory):
    year = date.today().year

    prioritization_criteria = fuzzy.FuzzyText()
    methodology_notes = fuzzy.FuzzyText()
    target_visits = fuzzy.FuzzyInteger(0, 100)
    modalities = fuzzy.FuzzyText()
    partner_engagement = fuzzy.FuzzyText()

    class Meta:
        model = YearPlan
        django_get_or_create = ('year',)


class BaseMonitoringActivityFactory(factory.DjangoModelFactory):
    # tpm_partner = factory.SubFactory(TPMPartnerFactory)
    activity_type = 'staff'
    location = factory.SubFactory(LocationFactory)

    start_date = date.today()
    end_date = date.today() + timedelta(days=30)

    questions__count = 0

    class Meta:
        model = MonitoringActivity

    @factory.post_generation
    def team_members(self, created, extracted, **kwargs):
        if extracted:
            self.team_members.add(*extracted)

    @factory.post_generation
    def sections(self, created, extracted, **kwargs):
        if extracted:
            self.sections.add(*extracted)

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

            ActivityQuestionFactory.create_batch(count, monitoring_activity=self)


class DraftActivityFactory(BaseMonitoringActivityFactory):
    status = MonitoringActivity.STATUSES.draft


class ChecklistActivityFactory(DraftActivityFactory):
    questions__count = 1
    status = MonitoringActivity.STATUSES.checklist


class ReviewActivityFactory(ChecklistActivityFactory):
    status = MonitoringActivity.STATUSES.review


class PreAssignedActivityFactory(ReviewActivityFactory):
    person_responsible = factory.SubFactory(UserFactory, unicef_user=True)
    field_office = factory.SubFactory(OfficeFactory)


class AssignedActivityFactory(ReviewActivityFactory):
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


class QuestionTemplateFactory(factory.DjangoModelFactory):
    question = factory.SubFactory(QuestionFactory)
    specific_details = fuzzy.FuzzyText()

    class Meta:
        model = QuestionTemplate
