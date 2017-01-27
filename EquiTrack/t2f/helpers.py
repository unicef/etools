from __future__ import unicode_literals

from collections import defaultdict, OrderedDict
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.utils.functional import cached_property

from django.core.exceptions import ObjectDoesNotExist

from publics.models import WBS, Grant, Fund


class PermissionMatrix(object):
    def __init__(self, travel, user):
        self.travel = travel
        self.user = user
        self._user_type = self.get_user_type()
        self._permission_dict = self.get_permission_dict()

    def get_user_type(self):
        from t2f.models import UserTypes
        return UserTypes.GOD

    def get_permission_dict(self):
        from t2f.models import TravelPermission
        permissions = TravelPermission.objects.filter(status=self.travel.status, user_type=self._user_type)
        return {(p.model, p.field, p.permission_type): p.value for p in permissions}

    def has_permission(self, permission_type, model_name, field_name):
        return self._permission_dict.get((permission_type, model_name, field_name), True)


class FakePermissionMatrix(PermissionMatrix):
    def __init__(self, user):
        super(FakePermissionMatrix, self).__init__(None, user)

    def has_permission(self, permission_type, model_name, field_name):
        return True

    def get_permission_dict(self):
        return {}


class CostSummaryCalculator(object):
    def __init__(self, travel):
        self.travel = travel
        self._dsa_region_cache = {}
        self._calculated = False

    def _init_values(self):
        self._dsa_data = []
        self._dsa_total = Decimal(0)
        self._total_deductions = Decimal(0)
        self._total_expenses = Decimal(0)

    def get_cost_summary(self):
        expenses = self._total_expenses.quantize(Decimal('1.0000'))
        if self.travel.preserved_expenses is not None:
            expenses_delta = self.travel.preserved_expenses - expenses
        else:
            expenses_delta = Decimal(0)
        result = {'dsa_total': self._dsa_total.quantize(Decimal('1.0000')),
                  'expenses_total': expenses,
                  'deductions_total': self._total_deductions.quantize(Decimal('1.0000')),
                  'dsa': self._dsa_data,
                  'preserved_expenses': self.travel.preserved_expenses,
                  'expenses_delta': expenses_delta}
        return result

    @cached_property
    def _itinerary(self):
        return list(self.travel.itinerary.all())

    @cached_property
    def date_deduction_mapping(self):
        deductions = self.travel.deductions.all()
        return self.get_date_deduction_mapping(deductions)

    def calculate_cost_summary(self):
        self._init_values()
        self._total_expenses = self._calculate_total_expenses()

        if not self._itinerary:
            return

        itinerary = list(self.travel.itinerary.order_by('departure_date'))

        region_to_daterange_mapping = self.get_dsa_region_collection(itinerary)

        counter = 0
        for dto in region_to_daterange_mapping:
            counter += 1

            itinerary_item = dto.itinerary_item
            region = dto.region
            start_date, end_date = dto.date_range
            night_count = (end_date - start_date).days + 1  # Last night should be counted too

            # Deduct overnight travels
            if itinerary_item.overnight_travel:
                overnight_count = (itinerary_item.arrival_date.date() - itinerary_item.departure_date.date()).days
            else:
                overnight_count = 0

            last_day = counter == len(itinerary)

            if night_count <= 60:
                accounted_night_count = night_count - overnight_count
                self.calculate_dsa(start_date, end_date, region, region.dsa_amount_usd, accounted_night_count, last_day)
            else:
                # Overnight count should be taken into account here since it affects the first days of travel and
                # not last
                # Edge case: overnight_count bigger than 60: user error
                accounted_night_count = 60 - overnight_count
                accounted_over60_nights_count = night_count - 60

                split_date = start_date + timedelta(days=59) # -1 because 60 days has 59 nights in between
                self.calculate_dsa(start_date, split_date, region, region.dsa_amount_usd,
                                   accounted_night_count, False) # Last day will be counted in the next call

                split_date += timedelta(days=1)
                self.calculate_dsa(split_date, end_date, region, region.dsa_amount_60plus_usd,
                                   accounted_over60_nights_count, last_day)

    def calculate_dsa(self, start_date, end_date, region, daily_rate, accounted_night_count, last_day):
        night_count = (end_date - start_date).days + 1

        if not last_day:
            deduction_multiplier = self.get_deduction_multiplier(start_date, end_date)
            deduction_multiplier = min(deduction_multiplier, accounted_night_count)
            deduction_amount = daily_rate * deduction_multiplier
            amount = daily_rate * accounted_night_count - deduction_amount
        else:
            # -1 because last day will be treated differently
            accounted_night_count -= 1

            deduction_multiplier = self.get_deduction_multiplier(start_date, end_date-timedelta(days=1))
            deduction_amount = daily_rate * deduction_multiplier
            amount = daily_rate * accounted_night_count - deduction_amount

            last_day_multiplier = self.get_deduction_multiplier(end_date, end_date)
            last_day_rate = daily_rate * Decimal('0.4')
            last_day_deduction_amount = last_day_rate * last_day_multiplier
            deduction_amount += last_day_deduction_amount
            # The inverted math is here because we are not deducting the deductions, rather multiplying the value with
            # the deductions multiplier
            amount += last_day_rate - last_day_deduction_amount

        dsa = {'start_date': start_date,
               'end_date': end_date,
               'dsa_region': region.id,
               'dsa_region_name': region.label,
               'night_count': night_count,
               'daily_rate_usd': daily_rate,
               'amount_usd': amount}

        self._dsa_data.append(dsa)
        self._dsa_total += amount + deduction_amount
        self._total_deductions += deduction_amount

    def get_deduction_multiplier(self, start_date, end_date):
        current_date = start_date
        multiplier = Decimal(0)

        while current_date <= end_date:
            multiplier += self.date_deduction_mapping.get(current_date, Decimal(0))
            current_date += timedelta(days=1)

        return multiplier

    def get_date_deduction_mapping(self, deductions_list):
        return {d.date: d.multiplier for d in deductions_list}

    def get_date_dsa_region_mapping(self, itinerary):
        if not itinerary:
            return []

        class DateRegionMapDTO(object):
            def __init__(self, itinerary_item, region, date):
                self.itinerary_item = itinerary_item
                self.region = region
                self.date = date

        mapping = OrderedDict()

        current_itinerary_item = itinerary[0]
        current_date = current_itinerary_item.departure_date.date()
        current_region = current_itinerary_item.dsa_region

        for itinerary_item in itinerary[1:]:
            end_date = itinerary_item.departure_date.date()

            while current_date < end_date:
                mapping[current_date] = DateRegionMapDTO(current_itinerary_item, current_region, current_date)
                current_date += timedelta(days=1)

            current_itinerary_item = itinerary_item
            current_region = itinerary_item.dsa_region

        end_date = current_itinerary_item.departure_date.date()
        while current_date <= end_date:
            mapping[current_date] = DateRegionMapDTO(current_itinerary_item, current_region, current_date)
            current_date += timedelta(days=1)

        return [dto for dto in mapping.values()]

    def get_dsa_region_collection(self, itinerary):
        class DSARegionDateRangeDTO(object):
            def __init__(self, itinerary_item, region, date_range):
                self.itinerary_item = itinerary_item
                self.region = region
                self.date_range = date_range

        date_dsa_region_mapping = self.get_date_dsa_region_mapping(itinerary)

        if not date_dsa_region_mapping:
            return []

        iterator = iter(date_dsa_region_mapping)
        dto = iterator.next()
        current_dto = dto
        date_range = [dto.date, dto.date]

        collection = []

        for dto in iterator:
            if dto.region == current_dto.region:
                date_range[1] = dto.date
                continue

            collection.append(DSARegionDateRangeDTO(current_dto.itinerary_item, current_dto.region, date_range))
            current_dto = dto
            date_range = [dto.date, dto.date]

        collection.append(DSARegionDateRangeDTO(current_dto.itinerary_item, current_dto.region, date_range))
        return collection


# ==========================================================================================================
    #     # All but last travel
    #     for item_id, itinerary_item in enumerate(itinerary_items_list[:-1]):
    #         start_date = itinerary_item.departure_date
    #         end_date = itinerary_items_list[item_id+1].departure_date
    #         self._calculate_dsa_for_timeframe(itinerary_item, start_date, end_date)
    #
    #     # Last travel
    #     # itinerary_item = itinerary_items_list[-1]
    #     # start_date = itinerary_item.departure_date.date()
    #     # # +1 day because of the < comparison
    #     # end_date = itinerary_item.arrival_date.date()
    #     # self._calculate_dsa_for_timeframe(itinerary_item, start_date, end_date, True)
    #
    # def _calculate_dsa_for_timeframe(self, itinerary_item, start_date, end_date, count_last_day=False):
    #     dsa_region = itinerary_item.dsa_region
    #
    #     timeframe_lenght = end_date - start_date
    #
    #     # First up to 60 days
    #     dsa = {'start_date': start_date,
    #            'end_date': end_date,
    #            'dsa_region': dsa_region.id,
    #            'dsa_region_name': dsa_region.name,
    #            'night_count': 0,
    #            'daily_rate_usd': Decimal(0),
    #            'amount_usd': Decimal(0)}
    #
    #     if timeframe_lenght.days > 60:
    #         # After 60th day
    #         dsa = {'start_date': start_date,
    #                'end_date': end_date,
    #                'dsa_region': dsa_region.id,
    #                'dsa_region_name': dsa_region.name,
    #                'night_count': 0,
    #                'daily_rate_usd': Decimal(0),
    #                'amount_usd': Decimal(0)}
    #
    #
    #
    #     # Old shit
    #     delta_day = timedelta(days=1)
    #
    #     dsa = {'start_date': start_date,
    #            'end_date': end_date,
    #            'dsa_region': dsa_region.id,
    #            'dsa_region_name': dsa_region.name}
    #
    #     if count_last_day:
    #         end_date += delta_day
    #
    #     night_count = Decimal((end_date - start_date).days)
    #     dsa['night_count'] = night_count
    #
    #     total_amount_usd = Decimal(0)
    #     current_day = start_date
    #     day_count = 1
    #     while current_day < end_date:
    #         last_day = (current_day+delta_day) >= end_date
    #
    #         if day_count <= 60:
    #             daily_rate = dsa_region.dsa_amount_usd
    #         else:
    #             daily_rate = dsa_region.dsa_amount_60plus_usd
    #
    #         if count_last_day and last_day:
    #             deduction_multiplier = Decimal('0.6')
    #         else:
    #             if itinerary_item.overnight_travel and current_day <= itinerary_item.departure_date.date():
    #                 overnight_travel = True
    #             else:
    #                 overnight_travel = False
    #             deduction_multiplier = self._get_deduction_multiplier_at(current_day, overnight_travel)
    #
    #         deduction = daily_rate * deduction_multiplier
    #         daily_rate -= deduction
    #
    #         total_amount_usd += daily_rate
    #         self._total_deductions += deduction
    #
    #         current_day += delta_day
    #         day_count += 1
    #
    #     if night_count:
    #         daily_rate_usd = total_amount_usd / night_count
    #     else:
    #         daily_rate_usd = total_amount_usd
    #
    #     dsa['daily_rate_usd'] = daily_rate_usd.quantize(Decimal('1.0000'))
    #     dsa['amount_usd'] = total_amount_usd.quantize(Decimal('1.0000'))
    #     self._dsa_data.append(dsa)
    #     self._dsa_total += total_amount_usd
    #

    def _calculate_total_expenses(self):
        return self.travel.expenses.all().aggregate(Sum('amount'))['amount__sum'] or Decimal(0)


class CloneTravelHelper(object):
    def __init__(self, travel):
        self.travel = travel

    def clone_for_secondary_traveler(self, new_traveler):
        fk_related = ['itinerary', 'expenses', 'deductions', 'cost_assignments']
        o2o_related = ['clearances']
        new_travel = self._do_the_cloning(new_traveler, fk_related, o2o_related)
        new_travel.activities = self.travel.activities.all()

        return new_travel

    def clone_for_driver(self, new_traveler):
        fk_related = ['itinerary']
        o2o_related = ['clearances']
        new_travel = self._do_the_cloning(new_traveler, fk_related, o2o_related)
        new_travel.is_driver = True
        new_travel.save()
        return new_travel

    def _do_the_cloning(self, new_traveler, fk_related, o2o_related):
        new_travel = self._clone_model(self.travel)
        new_travel.traveler = new_traveler
        new_travel.reset_status()
        new_travel.save()

        cloned_models = self._clone_related(fk_related, o2o_related)
        for new_related in cloned_models:
            new_related.travel = new_travel
            new_related.save()

        return new_travel

    def _clone_related(self, fk_related=None, o2o_related=None):
        fk_related = fk_related or []
        o2o_related = o2o_related or []
        cloned_models = []

        for relation_name in fk_related:
            related_qs = getattr(self.travel, relation_name).all()
            new_models = self._clone_model_list(related_qs)
            cloned_models.extend(new_models)

        for relation_name in o2o_related:
            try:
                related = getattr(self.travel, relation_name)
            except ObjectDoesNotExist:
                continue
            new_related = self._clone_model(related)
            cloned_models.append(new_related)

        return cloned_models

    def _clone_model_list(self, model_list):
        return map(self._clone_model, model_list)

    def _clone_model(self, model):
        from t2f.models import make_travel_reference_number

        new_instance = model.__class__.objects.get(pk=model.pk)
        new_instance.pk = None
        new_instance.id = None

        # TODO fix concurency
        new_instance.reference_number = make_travel_reference_number()
        return new_instance


class InvoiceMaker(object):
    USER_VENDOR_NUMBER = 'user'

    def __init__(self, travel):
        self.travel = travel

    def do_invoicing(self):
        existing_values = self.load_existing_invoices()
        current_values = self.get_current_values()
        delta_values = self.calculate_delta(existing_values, current_values)

        self.make_invoices(delta_values)

    def load_existing_invoices(self):
        vendor_grouping = defaultdict(lambda: defaultdict(Decimal))

        for invoice in self.travel.invoices.filter(status='success'):
            for item in invoice.items.all():
                key = (item.wbs.id, item.grant.id, item.fund.id)
                vendor_grouping[invoice.vendor_number][key] += item.amount

        return vendor_grouping

    def get_current_values(self):
        vendor_grouping = defaultdict(lambda: defaultdict(Decimal))
        cost_assignment_list = self.travel.cost_assignments.all()

        for expense in self.travel.expenses.all():
            vendor_number = expense.type.vendor_number

            # Parking expense
            if not vendor_number:
                continue

            if vendor_number.startswith('t_'):
                vendor_number = self.USER_VENDOR_NUMBER

            amount = expense.amount

            for ca in cost_assignment_list:
                key = (ca.wbs.id, ca.grant.id, ca.fund.id)
                share = Decimal(ca.share) / Decimal(100)
                vendor_grouping[vendor_number][key] += share * amount

        return vendor_grouping

    def calculate_delta(self, existing_values, current_values):
        vendor_grouping = deepcopy(current_values)

        for vendor_number in existing_values:
            for key, amount in existing_values[vendor_number].items():
                vendor_grouping[vendor_number][key] -= amount

        return vendor_grouping

    def make_invoices(self, vendor_grouping):
        from t2f.models import Invoice, InvoiceItem

        for vendor_number in vendor_grouping:
            if vendor_number == self.USER_VENDOR_NUMBER:
                currency = self.travel.currency
            else:
                expense = self.travel.expenses.get(type__vendor_number=vendor_number)
                currency = expense.account_currency

            invoice_kwargs = {'travel': self.travel,
                              'business_area': self.travel.traveler.profile.country.business_area_code,
                              'vendor_number': vendor_number,
                              'currency': currency,
                              'amount': Decimal(0),
                              'status': 'success'}

            items_list = []
            for key, amount in vendor_grouping[vendor_number].items():
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
            if not items_list:
                continue

            invoice = Invoice.objects.create(**invoice_kwargs)
            for item in items_list:
                item.invoice = invoice
                item.save()
