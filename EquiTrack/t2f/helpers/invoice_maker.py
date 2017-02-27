from __future__ import unicode_literals

from collections import defaultdict
from copy import deepcopy
from decimal import Decimal

from publics.models import WBS, Grant, Fund, TravelExpenseType


class InvoiceMaker(object):
    def __init__(self, travel):
        self.travel = travel
        self.user_vendor_number = self.travel.traveler.profile.vendor_number

    def do_invoicing(self):
        """Main entry point of the class"""
        existing_values = self.load_existing_invoices()
        current_values = self.get_current_values()
        delta_values = self.calculate_delta(existing_values, current_values)

        self.make_invoices(delta_values)

    def load_existing_invoices(self):
        """
        Loads the existing invoices and aggregates the values from them.
        Vendor grouping sample:
            {'vendor_num1': {('wbs_1', 'grant_1', 'fund_1'): 89,
                             ('wbs_1', 'grant_2', 'fund_2'): 11},
             'vendor_num2': {('wbs_1', 'grant_1', 'fund_1'): 56,
                             ('wbs_1', 'grant_2', 'fund_2'): 7}}
        :return: Aggregated values
        :rtype: dict
        """
        from t2f.models import Invoice

        vendor_grouping = defaultdict(lambda: defaultdict(Decimal))

        for invoice in self.travel.invoices.filter(status=Invoice.SUCCESS):
            for item in invoice.items.all():
                key = (item.wbs.id, item.grant.id, item.fund.id)
                vendor_grouping[invoice.vendor_number][key] += item.amount

        return vendor_grouping

    def get_current_values(self):
        """
        Loads the values from the actual travel based on the current values.
        Return value is the same data structure as above.

        :return: Aggregated values
        :rtype: dict
        """
        vendor_grouping = defaultdict(lambda: defaultdict(Decimal))
        cost_assignment_list = self.travel.cost_assignments.all()

        for expense in self.travel.expenses.exclude(amount=None):
            vendor_number = expense.type.vendor_number

            # Parking expense
            if not vendor_number:
                continue

            if vendor_number == TravelExpenseType.USER_VENDOR_NUMBER_PLACEHOLDER:
                vendor_number = self.user_vendor_number

            amount = expense.amount

            for ca in cost_assignment_list:
                key = (ca.wbs.id, ca.grant.id, ca.fund.id)
                share = Decimal(ca.share) / Decimal(100)
                vendor_grouping[vendor_number][key] += share * amount

        return vendor_grouping

    def calculate_delta(self, existing_values, current_values):
        """
        Calculates the difference between the previously loaded values and the current values and returns the diff in
        the same data structure as before.

        :param existing_values: Existing invoice values aggregated
        :type existing_values: dict
        :param current_values: Current travel values aggregated
        :type current_values: dict
        :return: Aggregated values
        :rtype: dict
        """
        vendor_grouping = deepcopy(current_values)

        for vendor_number in existing_values:
            for key, amount in existing_values[vendor_number].items():
                vendor_grouping[vendor_number][key] -= amount

        return vendor_grouping

    def make_invoices(self, vendor_grouping):
        """
        Based on the diff calculated before, makes the models for the newly created invoices.

        :param vendor_grouping: Diff of the previously generated invoices and current values
        :type vendor_grouping: dict
        """

        # This cannot be moved out from here, but since this class will be used when travel is sent for payment, the
        # speed impact is not so big
        from t2f.models import Invoice, InvoiceItem

        for vendor_number in vendor_grouping:
            if vendor_number == self.user_vendor_number:
                currency = self.travel.currency
            else:
                expense = self.travel.expenses.get(type__vendor_number=vendor_number)
                currency = expense.document_currency

            invoice_kwargs = {'travel': self.travel,
                              'business_area': self.travel.traveler.profile.country.business_area_code,
                              'vendor_number': vendor_number,
                              'currency': currency,
                              'amount': Decimal(0),
                              'status': Invoice.PENDING}

            items_list = []
            for key, amount in vendor_grouping[vendor_number].items():
                # In case there was no change, just skip it to avoid zero invoice items (lines on the invoice)
                if amount == 0:
                    continue

                wbs_id, grant_id, fund_id = key
                wbs = WBS.objects.get(id=wbs_id)
                grant = Grant.objects.get(id=grant_id)
                fund = Fund.objects.get(id=fund_id)

                invoice_item = InvoiceItem(wbs=wbs,
                                           grant=grant,
                                           fund=fund,
                                           amount=amount)
                items_list.append(invoice_item)
                invoice_kwargs['amount'] += amount

            # Don't make zero invoices
            # If item list is empty, there were no relevant changes at all (zero lines would be on the invoice)
            if not items_list:
                continue

            invoice = Invoice.objects.create(**invoice_kwargs)
            for item in items_list:
                item.invoice = invoice
                item.save()
