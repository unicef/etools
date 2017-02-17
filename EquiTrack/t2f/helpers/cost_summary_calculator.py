from __future__ import unicode_literals

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum


class CostSummaryCalculator(object):
    class ExpenseDTO(object):
        def __init__(self, vendor_number, amount):
            self.vendor_number = vendor_number
            self.amount = amount

    def __init__(self, travel):
        self.travel = travel

    def get_cost_summary(self):
        expense_mapping = self.get_expesnses()

        total_expense = sum(expense_mapping.values(), Decimal(0))
        total_expense = total_expense.quantize(Decimal('1.0000'))

        # Order the expenses
        expenses = []
        if 'user' in expense_mapping:
            expenses.append(self.ExpenseDTO('user', expense_mapping.pop('user')))
        parking_money = expense_mapping.pop('', None)

        travel_agent_expenses = sorted([self.ExpenseDTO(*e) for e in expense_mapping.items()],
                                       key=lambda o: o.vendor_number)
        expenses.extend(travel_agent_expenses)

        # explicit None checking should happen here otherwise the 0 will be filtered out
        if parking_money is not None:
            expenses.append(self.ExpenseDTO('', parking_money))

        if self.travel.preserved_expenses is not None:
            expenses_delta = self.travel.preserved_expenses - total_expense
        else:
            expenses_delta = Decimal(0)


        dsa_calculator = DSACalculator(self.travel)
        dsa_calculator.calculate_dsa()

        result = {'dsa_total': dsa_calculator.total_dsa.quantize(Decimal('1.0000')),
                  'expenses_total': total_expense,
                  'deductions_total': dsa_calculator.total_deductions.quantize(Decimal('1.0000')),
                  'dsa': dsa_calculator.detailed_dsa,
                  'preserved_expenses': self.travel.preserved_expenses,
                  'expenses_delta': expenses_delta,
                  'expenses': expenses}
        return result

    def get_expesnses(self):
        expenses_mapping = defaultdict(Decimal)
        expenses_qs = self.travel.expenses.select_related('type')
        for expense in expenses_qs:
            expenses_mapping[expense.type.vendor_number] += expense.amount
        return expenses_mapping


class DSACalculator(object):
    class DSAdto(object):
        def __init__(self, d, itinerary_item):
            self.itinerary_item = itinerary_item
            self.date = d
            self.region = itinerary_item.dsa_region
            self.dsa_amount = Decimal(0)
            self.deduction_multiplier = Decimal(0)

        def __repr__(self):
            return 'Date: {} | Region: {} | DSA amount: {} | Deduction: {} => Final: {}'.format(self.date,
                                                                                                self.region,
                                                                                                self.dsa_amount,
                                                                                                self.deduction,
                                                                                                self.final_amount)

        @property
        def final_amount(self):
            return self.dsa_amount - self.deduction

        @property
        def deduction(self):
            return self.dsa_amount * self.deduction_multiplier

    def __init__(self, travel):
        self.travel = travel
        self.total_dsa = None
        self.total_deductions = None
        self.detailed_dsa = None

    def _cast_datetime(self, dt):
        """
        :type dt: datetime.datetime
        :rtype: datetime.datetime
        """
        return dt

    def _cast_date(self, d):
        """
        :type d: datetime.date
        :rtype: datetime.date
        """
        return d

    def calculate_dsa(self):
        dsa_dto_list = self.get_by_day_grouping()
        dsa_dto_list = self.calculate_daily_dsa_rate(dsa_dto_list)
        dsa_dto_list = self.calculate_daily_deduction(dsa_dto_list)

        self.detailed_dsa = self.aggregate_detailed_dsa(dsa_dto_list)
        self.total_dsa = Decimal(0)
        self.total_deductions = Decimal(0)
        for dto in dsa_dto_list:
            self.total_dsa += dto.final_amount

            if dto == dsa_dto_list[-1]:
                dto.deduction_multiplier -= Decimal('0.6')

            self.total_deductions += dto.deduction

    def aggregate_detailed_dsa(self, dsa_dto_list):
        detailed_dsa = []
        previous_region = None
        current_data = None

        for dto in dsa_dto_list:
            if previous_region != dto.region:
                # If there is data, put to the result list
                if current_data:
                    detailed_dsa.append(current_data)

                # Create new data holder
                current_data = {'start_date': dto.date,
                                'end_date': dto.date,
                                'dsa_region': dto.region.id,
                                'dsa_region_name': dto.region.label,
                                'night_count': -1, # -1 because nights are always days-1
                                'daily_rate_usd': dto.region.dsa_amount_usd,
                                'amount_usd': Decimal(0)}
                previous_region = dto.region

            current_data['end_date'] = dto.date
            current_data['night_count'] += 1
            current_data['amount_usd'] += dto.final_amount

        if current_data:
            detailed_dsa.append(current_data)

        return detailed_dsa

    def get_by_day_grouping(self):
        """
        Returns a mapping where the key represents the day, the value represents the DSA Region applied
        """
        mapping = {}

        itinerary_item_list = list(self.travel.itinerary.order_by('arrival_date'))

        # To few elements, cannot calculate properly
        if len(itinerary_item_list) < 2:
            return []

        for itinerary_item in itinerary_item_list[:-1]:
            arrival_date = self._cast_datetime(itinerary_item.arrival_date).date()
            mapping[arrival_date] = itinerary_item

        start_date = self._cast_datetime(itinerary_item_list[0].arrival_date).date()
        end_date = self._cast_datetime(itinerary_item_list[-1].departure_date).date()

        tmp_date = start_date
        previous_itinerary = None
        while tmp_date <= end_date:
            if tmp_date in mapping:
                previous_itinerary = mapping[tmp_date]
            else:
                mapping[tmp_date] = previous_itinerary
            tmp_date += timedelta(days=1)

        dsa_dto_list = []
        for date, itinerary in mapping.items():
            dto = self.DSAdto(date, itinerary)
            dsa_dto_list.append(dto)

        return sorted(dsa_dto_list, cmp=lambda x, y: cmp(x.date, y.date))

    def calculate_daily_dsa_rate(self, dsa_dto_list):
        if not dsa_dto_list:
            return dsa_dto_list

        day_counter = 1

        for dto in dsa_dto_list:
            departure_date = self._cast_datetime(dto.itinerary_item.departure_date).date()
            if departure_date != dto.date or not dto.itinerary_item.overnight_travel:
                if day_counter <= 60:
                    dto.dsa_amount += dto.region.dsa_amount_usd
                else:
                    dto.dsa_amount += dto.region.dsa_amount_60plus_usd

            # Last day does not add same day travel
            if dto != dsa_dto_list[-1]:
                self.add_same_day_travels(dto, day_counter)

            day_counter += 1

        return dsa_dto_list

    def add_same_day_travels(self, dto, day_counter):
        # Check if there were any extra travel on that day
        same_day_travels = self.travel.itinerary.exclude(dsa_region=dto.region)
        same_day_travels = same_day_travels.filter(departure_date__year=dto.date.year,
                                                   departure_date__month=dto.date.month,
                                                   departure_date__day=dto.date.day)

        same_day_travels = list(same_day_travels)
        same_day_travels.append(dto.itinerary_item)
        for i, sdt in enumerate(same_day_travels[:-1]):
            # If it was less than 8 hours long, skip it
            arrival = sdt.arrival_date
            departure = same_day_travels[i+1].departure_date
            if (departure - arrival) < timedelta(hours=8):
                continue

            if day_counter <= 60:
                same_day_dsa = sdt.dsa_region.dsa_amount_usd
            else:
                same_day_dsa = sdt.dsa_region.dsa_amount_60plus_usd

            dto.dsa_amount += same_day_dsa * Decimal('0.4')

    def calculate_daily_deduction(self, dsa_dto_list):
        if not dsa_dto_list:
            return dsa_dto_list

        deduction_mapping = {d.date: d.multiplier for d in self.travel.deductions.all()}

        for dto in dsa_dto_list:
            dto.deduction_multiplier = deduction_mapping.get(dto.date, Decimal(0))

        # If it's the last day, 40% of dsa should go only, so apply a 60% deduction
        last_day_dto = dsa_dto_list[-1]
        new_deduction_multiplier = last_day_dto.deduction_multiplier + Decimal('0.6')
        last_day_dto.deduction_multiplier = min(new_deduction_multiplier, Decimal(1))

        return dsa_dto_list
