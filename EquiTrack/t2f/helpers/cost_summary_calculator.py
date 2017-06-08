from __future__ import unicode_literals

from collections import defaultdict, OrderedDict
from datetime import timedelta
from decimal import Decimal
from itertools import chain


class CostSummaryCalculator(object):
    class ExpenseDTO(object):
        def __init__(self, vendor_number, expense):
            self.vendor_number = vendor_number
            self.label = expense.type.title
            self.currency = expense.currency
            self.amount = expense.amount

    def __init__(self, travel):
        self.travel = travel

    def get_cost_summary(self):
        expense_mapping = self.get_expenses()

        sorted_expense_mapping_values = chain.from_iterable(expense_mapping.values())
        local_expenses = [e.amount for e in sorted_expense_mapping_values
                          if e.currency == self.travel.currency]
        total_expense_local = sum(local_expenses, Decimal(0))
        total_expense_local = total_expense_local.quantize(Decimal('1.0000'))

        usd_expenses = [e.usd_amount for e in sorted_expense_mapping_values
                        if e.currency != self.travel.currency and e.usd_amount]
        total_expense_usd = sum(usd_expenses, Decimal(0))
        total_expense_usd = total_expense_usd.quantize(Decimal('1.0000'))

        # Order the expenses
        expenses = []
        for expense in expense_mapping.pop('user', []):
            expenses.append(self.ExpenseDTO('user', expense))

        parking_money = expense_mapping.pop('', [])

        # Create data transfer object for each expense
        travel_agent_expenses = []
        for key, values in expense_mapping.items():
            travel_agent_expenses.extend(self.ExpenseDTO(key, e) for e in values)
        travel_agent_expenses = sorted(travel_agent_expenses, key=lambda o: o.vendor_number)
        expenses.extend(travel_agent_expenses)

        for parking_money_expense in parking_money:
            expenses.append(self.ExpenseDTO('', parking_money_expense))

        if self.travel.preserved_expenses_local is not None:
            expenses_delta_local = self.travel.preserved_expenses_local - total_expense_local
        else:
            expenses_delta_local = Decimal(0)

        if self.travel.preserved_expenses_usd is not None:
            expenses_delta_usd = self.travel.preserved_expenses_usd - total_expense_usd
        else:
            expenses_delta_usd = Decimal(0)

        dsa_calculator = DSACalculator(self.travel)
        dsa_calculator.calculate_dsa()

        expenses_total = OrderedDict()
        paid_to_traveler = dsa_calculator.paid_to_traveler.quantize(Decimal('1.0000'))
        for expense in expenses:
            if expense.currency not in expenses_total:
                expenses_total[expense.currency] = Decimal(0)
            expenses_total[expense.currency] += expense.amount

            if expense.vendor_number == 'user':
                paid_to_traveler += expense.amount

        expenses_total = [{'currency': k, 'amount': v} for k, v in expenses_total.items()]

        result = {'dsa_total': dsa_calculator.total_dsa,
                  'dsa': dsa_calculator.detailed_dsa,
                  'deductions_total': dsa_calculator.total_deductions.quantize(Decimal('1.0000')),
                  'traveler_dsa': dsa_calculator.paid_to_traveler.quantize(Decimal('1.0000')),
                  'expenses_total': expenses_total,
                  'preserved_expenses': self.travel.preserved_expenses_local,
                  'expenses_delta': expenses_delta_local,
                  'expenses_delta_local': expenses_delta_local,
                  'expenses_delta_usd': expenses_delta_usd,
                  'expenses': expenses,
                  'paid_to_traveler': paid_to_traveler}
        return result

    def get_expenses(self):
        expenses_mapping = OrderedDict()
        expenses_qs = self.travel.expenses.exclude(amount=None).select_related('type').order_by('id')

        for expense in expenses_qs:
            if expense.type.vendor_number not in expenses_mapping:
                expenses_mapping[expense.type.vendor_number] = []

            expenses_mapping[expense.type.vendor_number].append(expense)
        return expenses_mapping


class DSACalculator(object):
    LAST_DAY_DEDUCTION = Decimal('0.6')
    SAME_DAY_TRAVEL_MULTIPLIER = Decimal('0.4')
    USD_CODE = 'USD'

    class DSAdto(object):
        def __init__(self, d, itinerary_item):
            self.date = d
            self.set_itinerary_item(itinerary_item)

            self.dsa_amount = Decimal(0)
            self.deduction_multiplier = Decimal(0)
            self.last_day = False

        def set_itinerary_item(self, itinerary_item):
            self.itinerary_item = itinerary_item
            self.region = itinerary_item.dsa_region

        def __repr__(self):
            return 'Date: {} | Region: {} | DSA amount: {} | Deduction: {} => Final: {}'.format(self.date,
                                                                                                self.region,
                                                                                                self.dsa_amount,
                                                                                                self.deduction,
                                                                                                self.final_amount)

        @property
        def corrected_dsa_amount(self):
            if self.last_day:
                return self.dsa_amount - (self.dsa_amount * DSACalculator.LAST_DAY_DEDUCTION)
            return self.dsa_amount

        @property
        def final_amount(self):
            final_amount = self.dsa_amount - self._internal_deduction
            final_amount -= self.deduction
            return max(final_amount, Decimal(0))

        @property
        def deduction(self):
            multiplier = self.deduction_multiplier
            if self.last_day:
                multiplier = min(multiplier, Decimal(1)-DSACalculator.LAST_DAY_DEDUCTION)
            return self.dsa_amount * multiplier

        @property
        def _internal_deduction(self):
            if self.last_day:
                return self.dsa_amount * DSACalculator.LAST_DAY_DEDUCTION
            return Decimal(0)

    def __init__(self, travel):
        self.travel = travel
        self.total_dsa = None
        self.total_deductions = None
        self.paid_to_traveler = None
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
        # If TA not required, dsa amounts should be zero
        dsa_should_be_zero = False
        if not self.travel.ta_required:
            dsa_should_be_zero = True

        if self.travel.itinerary.filter(dsa_region=None).exists():
            dsa_should_be_zero = True

        if dsa_should_be_zero:
            self.total_dsa = Decimal(0)
            self.total_deductions = Decimal(0)
            self.paid_to_traveler = Decimal(0)
            self.detailed_dsa = []
            return

        dsa_dto_list = self.get_by_day_grouping()
        dsa_dto_list = self.check_one_day_long_trip(dsa_dto_list)
        dsa_dto_list = self.calculate_daily_dsa_rate(dsa_dto_list)
        dsa_dto_list = self.calculate_daily_deduction(dsa_dto_list)
        dsa_dto_list = self.check_last_day(dsa_dto_list)

        self.total_dsa = Decimal(0)
        self.total_deductions = Decimal(0)
        self.paid_to_traveler = Decimal(0)
        for dto in dsa_dto_list:
            self.paid_to_traveler += dto.final_amount
            self.total_dsa += dto.corrected_dsa_amount
            self.total_deductions += dto.deduction
        self.detailed_dsa = self.aggregate_detailed_dsa(dsa_dto_list)

    def get_dsa_amount(self, dsa_region, over_60_days):
        dsa_rate = dsa_region.get_rate_at(self.travel.submitted_at)

        if self.travel.currency:
            currency = 'usd' if self.travel.currency.code == self.USD_CODE else 'local'
        else:
            currency = 'local'
        over_60 = '60plus_' if over_60_days else ''
        field_name = 'dsa_amount_{over_60}{currency}'.format(over_60=over_60, currency=currency)
        return getattr(dsa_rate, field_name)

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
        counter = 1
        for date, itinerary in mapping.items():
            dto = self.DSAdto(date, itinerary)
            over_60 = counter > 60
            dto.daily_rate = self.get_dsa_amount(dto.region, over_60)
            dsa_dto_list.append(dto)
            counter += 1

        return sorted(dsa_dto_list, cmp=lambda x, y: cmp(x.date, y.date))

    def check_one_day_long_trip(self, dsa_dto_list):
        # If it's a day long trip and only one less than 8 hour travel was made, no dsa applied
        if not dsa_dto_list:
            return dsa_dto_list

        if len(dsa_dto_list) > 1:
            return dsa_dto_list

        same_day_travels = list(self.travel.itinerary.all())
        for i, sdt in enumerate(same_day_travels[:-1]):
            # If it was less than 8 hours long, skip it
            arrival = sdt.arrival_date
            departure = same_day_travels[i+1].departure_date
            if (departure - arrival) >= timedelta(hours=8):
                break
        else:
            # No longer than 8 hours travel found, no dsa should be applied
            return []

        return dsa_dto_list

    def calculate_daily_dsa_rate(self, dsa_dto_list):
        if not dsa_dto_list:
            return dsa_dto_list

        day_counter = 1

        for dto in dsa_dto_list:
            departure_date = self._cast_datetime(dto.itinerary_item.departure_date).date()
            if departure_date != dto.date or not dto.itinerary_item.overnight_travel:
                over_60 = day_counter > 60
                dto.dsa_amount += self.get_dsa_amount(dto.region, over_60)

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

            over_60 = day_counter > 60
            same_day_dsa = self.get_dsa_amount(sdt.dsa_region, over_60)
            dto.dsa_amount += same_day_dsa * self.SAME_DAY_TRAVEL_MULTIPLIER

    def calculate_daily_deduction(self, dsa_dto_list):
        if not dsa_dto_list:
            return dsa_dto_list

        deduction_mapping = {d.date: d.multiplier for d in self.travel.deductions.all()}

        for dto in dsa_dto_list:
            dto.deduction_multiplier = deduction_mapping.get(dto.date, Decimal(0))

        return dsa_dto_list

    def check_last_day(self, dsa_dto_list):
        if not dsa_dto_list:
            return dsa_dto_list

        last_dto = dsa_dto_list[-1]
        last_day_departure_count = self.travel.itinerary.filter(departure_date__year=last_dto.date.year,
                                                                departure_date__month=last_dto.date.month,
                                                                departure_date__day=last_dto.date.day).count()


        itinerary = self.travel.itinerary.order_by('-departure_date')
        if last_day_departure_count and itinerary.count() > last_day_departure_count:
            first_departure = itinerary[last_day_departure_count]

            last_dto.set_itinerary_item(first_departure)
            over_60 = len(dsa_dto_list) > 60
            dsa_amount = self.get_dsa_amount(last_dto.region, over_60)
            last_dto.dsa_amount = dsa_amount

        last_dto.last_day = True
        return dsa_dto_list

    def aggregate_detailed_dsa(self, dsa_dto_list):
        detailed_dsa = []
        previous_region = None
        current_data = None

        for day_index, dto in enumerate(dsa_dto_list):
            if previous_region != dto.region or day_index == 60:
                # If there is data, put to the result list
                if current_data:
                    detailed_dsa.append(current_data)

                # Create new data holder
                over_60 = day_index >= 60   # bigger or equal (not just bigger) because index starts from zero
                current_data = {'start_date': dto.date,
                                'end_date': dto.date,
                                'dsa_region': dto.region.id,
                                'dsa_region_name': dto.region.label,
                                'night_count': -1, # -1 because nights are always days-1
                                'daily_rate': self.get_dsa_amount(dto.region, over_60),
                                'paid_to_traveler': Decimal(0),
                                'total_amount': Decimal(0),
                                'deduction': Decimal(0)}
                previous_region = dto.region

            current_data['end_date'] = dto.date
            current_data['night_count'] += 1
            current_data['paid_to_traveler'] += dto.final_amount
            current_data['total_amount'] += dto.corrected_dsa_amount
            current_data['deduction'] += dto.deduction

        if current_data:
            detailed_dsa.append(current_data)

        return detailed_dsa
