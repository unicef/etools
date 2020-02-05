from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.offline.errors import MissingRequiredValueError
from etools.applications.offline.fields import TextField
from etools.applications.offline.fields.base import SkipField
from etools.applications.offline.metadata import Metadata


class TestTextField(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.meta = Metadata()

    def test_integer_cast_to_text(self):
        self.assertEqual(TextField('test').validate(1, self.meta), '1')

    def test_required(self):
        with self.assertRaises(MissingRequiredValueError):
            TextField('test').validate(None, self.meta)

        with self.assertRaises(SkipField):
            TextField('test', required=False).validate(None, self.meta)
