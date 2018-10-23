from django.core.exceptions import ValidationError

from factory import fuzzy

from unicef_locations.tests.factories import LocationFactory

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.models import MethodType
from etools.applications.field_monitoring.tests.factories import MethodFactory, SiteFactory


class MethodTypeTestCase(BaseTenantTestCase):
    def test_types_non_applicable(self):
        method = MethodFactory(is_types_applicable=False)

        with self.assertRaises(ValidationError):
            MethodType(method=method, name=fuzzy.FuzzyText().fuzz()).clean()

    def test_types_applicable(self):
        method = MethodFactory(is_types_applicable=True)
        MethodType(method=method, name=fuzzy.FuzzyText().fuzz()).clean()


class SitesTestCase(BaseTenantTestCase):
    def test_parent_not_allowed(self):
        parent_location = LocationFactory(parent=LocationFactory())
        site = SiteFactory.build(parent=parent_location.parent)
        with self.assertRaises(ValidationError):
            site.clean()

    def test_parent_allowed(self):
        location = LocationFactory()
        site = SiteFactory.build(parent=location)
        site.clean()

    def test_gateway_assigned(self):
        site = SiteFactory(gateway=None)
        self.assertIsNotNone(site.gateway)

    def test_inactive_location(self):
        # test parent will not be broken with custom manager after deactivation
        site = SiteFactory()
        site.parent.is_active = False
        site.parent.save()
        type(site).objects.get(id=site.id)
        self.assertIsNotNone(site.parent)
