from django.core.exceptions import ValidationError
from factory import fuzzy

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.field_monitoring.models import MethodType
from etools.applications.field_monitoring.tests.factories import MethodFactory


class MethodTypeTestCase(BaseTenantTestCase):
    def test_types_non_applicable(self):
        method = MethodFactory(is_types_applicable=False)

        with self.assertRaises(ValidationError):
            MethodType(method=method, name=fuzzy.FuzzyText().fuzz()).clean()

    def test_types_applicable(self):
        method = MethodFactory(is_types_applicable=True)
        MethodType(method=method, name=fuzzy.FuzzyText().fuzz()).clean()
