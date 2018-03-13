from __future__ import unicode_literals

from EquiTrack.tests.mixins import APITenantTestCase
from publics.models import TravelExpenseType
from publics.tests.factories import PublicsCurrencyFactory, PublicsTravelExpenseTypeFactory
from t2f.models import Expense, Travel
from users.tests.factories import UserFactory


class TravelMethods(APITenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.traveler = UserFactory()

        profile = cls.traveler.profile
        profile.vendor_number = 'user0001'
        profile.save()

        country = profile.country
        country.business_area_code = '0060'
        country.save()

    def test_cost_summary(self):
        # Currencies
        huf = PublicsCurrencyFactory(name='HUF', code='huf')

        # Expense types
        et_t_food = PublicsTravelExpenseTypeFactory(
            title='Food',
            vendor_number=TravelExpenseType.USER_VENDOR_NUMBER_PLACEHOLDER
        )
        et_t_travel = PublicsTravelExpenseTypeFactory(
            title='Travel',
            vendor_number=TravelExpenseType.USER_VENDOR_NUMBER_PLACEHOLDER
        )
        et_t_other = PublicsTravelExpenseTypeFactory(
            title='Other',
            vendor_number=TravelExpenseType.USER_VENDOR_NUMBER_PLACEHOLDER
        )

        # Make a travel
        travel = Travel.objects.create(traveler=self.traveler,
                                       supervisor=self.unicef_staff,
                                       currency=huf)

        # Add expenses
        Expense.objects.create(travel=travel,
                               type=et_t_food,
                               currency=huf,
                               amount=35)

        Expense.objects.create(travel=travel,
                               type=et_t_travel,
                               currency=huf,
                               amount=50)

        Expense.objects.create(travel=travel,
                               type=et_t_other,
                               currency=huf,
                               amount=15)

        Expense.objects.create(travel=travel,
                               type=et_t_travel,
                               currency=huf,
                               amount=None)

        # This should not raise 500
        travel.cost_summary
