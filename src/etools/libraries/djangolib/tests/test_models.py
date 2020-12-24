from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.publics.models import Currency
from etools.libraries.djangolib.models import EPOCH_ZERO


class TestSoftDeleteMixin(BaseTenantTestCase):
    def test_queryset_filter(self):
        self.assertEqual(Currency.objects.count(), 0)

        currency = Currency.objects.create()
        Currency.objects.create().delete()

        self.assertEqual(Currency.objects.count(), 1)
        self.assertEqual(Currency.objects.first().pk, currency.pk)

        self.assertEqual(Currency.admin_objects.count(), 2)

    def test_sort_delete(self):
        currency = Currency.objects.create()
        currency.delete()

        currency_from_db = Currency.admin_objects.filter(pk=currency.pk).first()
        self.assertIsNotNone(currency_from_db)
        self.assertNotEqual(currency_from_db.deleted_at, EPOCH_ZERO)

    def test_force_delete(self):
        currency = Currency.objects.create()
        currency.force_delete()

        currency_from_db = Currency.admin_objects.filter(pk=currency.pk).first()
        self.assertIsNone(currency_from_db)
