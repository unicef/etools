from datetime import date, timedelta

import factory
from factory import fuzzy
from unicef_locations.tests.factories import LocationFactory

from etools.applications.field_monitoring.planning.models import YearPlan, MonitoringActivity
from etools.applications.tpm.tests.factories import TPMPartnerFactory


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


class MonitoringActivityFactory(factory.DjangoModelFactory):
    # tpm_partner = factory.SubFactory(TPMPartnerFactory)
    activity_type = 'staff'
    location = factory.SubFactory(LocationFactory)

    start_date = date.today()
    end_date = date.today() + timedelta(days=30)

    class Meta:
        model = MonitoringActivity
