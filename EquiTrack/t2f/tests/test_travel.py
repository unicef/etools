from __future__ import unicode_literals

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase
from publics.models import TravelExpenseType

from t2f.models import Travel, Expense
from t2f.tests.factories import CurrencyFactory, ExpenseTypeFactory


class TravelMethods(APITenantTestCase):
    def setUp(self):
        super(TravelMethods, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)
        self.traveler = UserFactory()

        profile = self.traveler.profile
        profile.vendor_number = 'user0001'
        profile.save()

        country = profile.country
        country.business_area_code = '0060'
        country.save()

    def test_cost_summary(self):
        # Currencies
        huf = CurrencyFactory(name='HUF',
                              code='huf')

        # Expense types
        et_t_food = ExpenseTypeFactory(title='Food', vendor_number=TravelExpenseType.USER_VENDOR_NUMBER_PLACEHOLDER)
        et_t_travel = ExpenseTypeFactory(title='Travel', vendor_number=TravelExpenseType.USER_VENDOR_NUMBER_PLACEHOLDER)
        et_t_other = ExpenseTypeFactory(title='Other', vendor_number=TravelExpenseType.USER_VENDOR_NUMBER_PLACEHOLDER)

        # Make a travel
        travel = Travel.objects.create(traveler=self.traveler,
                                       supervisor=self.unicef_staff,
                                       currency=huf)

        # Add expenses
        Expense.objects.create(travel=travel,
                               type=et_t_food,
                               document_currency=huf,
                               account_currency=huf,
                               amount=35)

        Expense.objects.create(travel=travel,
                               type=et_t_travel,
                               document_currency=huf,
                               account_currency=huf,
                               amount=50)

        Expense.objects.create(travel=travel,
                               type=et_t_other,
                               document_currency=huf,
                               account_currency=huf,
                               amount=15)

        Expense.objects.create(travel=travel,
                               type=et_t_travel,
                               document_currency=huf,
                               account_currency=huf,
                               amount=None)

        # This should not raise 500
        travel.cost_summary
