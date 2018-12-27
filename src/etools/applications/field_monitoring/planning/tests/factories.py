from datetime import date

import factory
from factory import fuzzy

from etools.applications.field_monitoring.planning.models import YearPlan, Task
from etools.applications.field_monitoring.fm_settings.tests.factories import CPOutputConfigFactory, LocationSiteFactory
from etools.applications.reports.tests.factories import SectionFactory
from etools.applications.tpm.tests.factories import FullInterventionFactory


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


class TaskFactory(factory.DjangoModelFactory):
    year_plan = factory.SubFactory(YearPlanFactory)

    intervention = factory.SubFactory(FullInterventionFactory)
    partner = factory.LazyAttribute(lambda o: o.intervention.agreement.partner)

    cp_output_config = factory.LazyAttribute(
        lambda o: CPOutputConfigFactory(cp_output=o.intervention.result_links.first().cp_output)
    )

    location_site = factory.SubFactory(LocationSiteFactory)
    location = factory.LazyAttribute(lambda o: o.location_site.parent)

    sections__count = 0

    class Meta:
        model = Task

    @factory.post_generation
    def sections(self, created, extracted, count, **kwargs):
        if created:
            self.sections.add(*[SectionFactory() for i in range(count)])

        if extracted:
            self.sections.add(*extracted)
