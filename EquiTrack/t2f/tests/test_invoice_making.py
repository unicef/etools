from __future__ import unicode_literals

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase

from t2f.helpers import InvoiceMaker
from t2f.models import Travel, Expense, CostAssignment, InvoiceItem
from t2f.tests.factories import CurrencyFactory, ExpenseTypeFactory, WBSFactory, GrantFactory, FundFactory
from t2f.views import make_invoices


class TravelDetails(APITenantTestCase):
    def setUp(self):
        super(TravelDetails, self).setUp()
        self.traveler = UserFactory()
        country = self.traveler.profile.country
        country.business_area_code = '0060'
        country.save()
        self.unicef_staff = UserFactory(is_staff=True)

    def test_invoice_making(self):
        # Currencies
        usd = CurrencyFactory(name='USD',
                              iso_4217='usd')
        huf = CurrencyFactory(name='HUF',
                              iso_4217='huf')

        # Add wbs/grant/fund
        wbs_1 = WBSFactory(name='WBS #1')
        wbs_2 = WBSFactory(name='WBS #2')

        grant_1 = GrantFactory(name='Grant #1', wbs=wbs_1)
        grant_2 = GrantFactory(name='Grant #2', wbs=wbs_2)
        grant_3 = GrantFactory(name='Grant #3', wbs=wbs_2)

        fund_1 = FundFactory(name='Fund #1', grant=grant_1)
        fund_2 = FundFactory(name='Fund #2', grant=grant_2)
        fund_3 = FundFactory(name='Fund #3', grant=grant_3)
        fund_4 = FundFactory(name='Fund #4', grant=grant_3)

        # Expense types
        et_t_food = ExpenseTypeFactory(title='Food', code='t_food')
        et_t_travel = ExpenseTypeFactory(title='Travel', code='t_travel')
        et_t_other = ExpenseTypeFactory(title='Other', code='t_other')

        et_a_andras = ExpenseTypeFactory(title='Andras Travel', code='a_andras')
        et_a_nico = ExpenseTypeFactory(title='Nico Travel', code='a_nico')
        et_a_torben = ExpenseTypeFactory(title='Torben Travel', code='a_torben')

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

        expense_other = Expense.objects.create(travel=travel,
                                               type=et_t_other,
                                               document_currency=huf,
                                               account_currency=huf,
                                               amount=15)

        # Add cost assignments
        ca_1 = CostAssignment.objects.create(travel=travel,
                                             share=70,
                                             wbs=wbs_1,
                                             grant=grant_1,
                                             fund=fund_1)
        ca_2 = CostAssignment.objects.create(travel=travel,
                                             share=30,
                                             wbs=wbs_2,
                                             grant=grant_3,
                                             fund=fund_4)

        # Do the testing
        self.assertEqual(travel.invoices.all().count(), 0)
        self.assertEqual(InvoiceItem.objects.all().count(), 0)

        # Generate invoice
        make_invoices(travel)

        self.assertEqual(travel.invoices.all().count(), 1)
        self.assertEqual(InvoiceItem.objects.all().count(), 2)

        # Add more stuff
        expense_other.amount = 45
        expense_other.save()

        Expense.objects.create(travel=travel,
                               type=et_a_nico,
                               document_currency=huf,
                               account_currency=huf,
                               amount=1000)
        Expense.objects.create(travel=travel,
                               type=et_a_torben,
                               document_currency=huf,
                               account_currency=huf,
                               amount=500)

        # Generate invoice
        make_invoices(travel)

        self.assertEqual(travel.invoices.all().count(), 4)
        self.assertEqual(InvoiceItem.objects.all().count(), 8)

        # Remove a cost assignment
        ca_1.share = 100
        ca_1.save()
        ca_2.delete()

        # Generate invoice
        make_invoices(travel)
