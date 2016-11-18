from __future__ import unicode_literals

from datetime import timedelta
from decimal import Decimal as D

from django.core.exceptions import ObjectDoesNotExist

from et2f import UserTypes


class PermissionMatrix(object):
    def __init__(self, travel, user):
        self.travel = travel
        self.user = user
        self._user_type = self.get_user_type()
        self._permission_dict = self.get_permission_dict()

    def get_user_type(self):
        return UserTypes.GOD

    def get_permission_dict(self):
        # TODO simon: this is bad. fix it somehow
        from et2f.models import TravelPermission
        permissions = TravelPermission.objects.filter(status=self.travel.status, user_type=self._user_type)
        return {(p.model, p.field, p.permission_type): p.value for p in permissions}

    def has_permission(self, permission_type, model_name, field_name):
        return self._permission_dict.get((permission_type, model_name, field_name), True)


class CostSummaryCalculator(object):
    def __init__(self, travel):
        self.travel = travel
        self._dsa_region_cache = {}

    def calculate_cost_summary(self):
        result = {'dsa_total': self.calculate_total_dsa(),
                  'expenses_total': self.calculate_total_expenses(),
                  'deductions_total': self.calculate_total_deductions()}
        return result

    def _get_dsa_region_at(self, date):
        """
        :type date: datetime.date
        :rtype: et2f.models.DSARegion | None
        """
        if date not in self._dsa_region_cache:
            last_itinerary_item = self.travel.itinerary.filter(departure_date__year=date.year,
                                                               departure_date__month=date.month,
                                                               departure_date__day=date.day,
                                                               arrival_date__year=date.year,
                                                               arrival_date__month=date.month,
                                                               arrival_date__day=date.day).last()
            self._dsa_region_cache[date] = getattr(last_itinerary_item, 'dsa_region', None)
        return self._dsa_region_cache[date]

    def _get_dsa_rate_at(self, date, since=1):
        dsa_region = self._get_dsa_region_at(date)
        if dsa_region is None:
            return D(0)
        if since <= 60:
            return dsa_region.dsa_amount_usd
        return dsa_region.dsa_amount_60plus_usd

    def _get_deduction_multiplier_at(self, date):
        multiplier = D(0)

        try:
            deduction = self.travel.deductions.get(date=date)
        except ObjectDoesNotExist:
            return multiplier

        # TODO handle overnight
        if deduction.no_dsa:
            multiplier += D(1)
        if deduction.breakfast:
            multiplier += D('0.05')
        if deduction.lunch:
            multiplier += D('0.1')
        if deduction.dinner:
            multiplier += D('0.15')
        if deduction.accomodation:
            multiplier += D('0.5')

        # Handle if it goes above 1
        return min(multiplier, 1)

    def _get_deduction_at(self, date):
        dsa_rate = self._get_dsa_rate_at(date)
        multiplier = self._get_deduction_multiplier_at(date)
        return dsa_rate * multiplier

    def calculate_total_dsa(self):
        current_date = self.travel.start_date.date()
        end_date = self.travel.end_date.date()
        step = timedelta(days=1)

        previous_region = None
        previous_region_since = 0

        total = D(0)
        while current_date <= end_date:
            dsa_region = self._get_dsa_region_at(current_date)
            if dsa_region == previous_region:
                previous_region_since += 1
            else:
                previous_region = dsa_region
                previous_region_since = 1

            dsa_rate = self._get_dsa_rate_at(current_date, previous_region_since)
            if current_date == end_date:
                dsa_rate *= D('0.4')
            else:
                deductions = self._get_deduction_at(current_date)
                dsa_rate -= deductions

            total += dsa_rate

            current_date += step

        return total

    def calculate_total_expenses(self):
        # TODO: figure out how to handle different currencies
        total = D(0)
        for expense in self.travel.expenses.all():
            total += expense.amount
        return total

    def calculate_total_deductions(self):
        current_date = self.travel.start_date.date()
        end_date = self.travel.end_date.date()
        step = timedelta(days=1)

        total = D(0)
        while current_date <= end_date:
            total += self._get_deduction_at(current_date)
            current_date += step

        return total


class CloneTravelHelper(object):
    def __init__(self, travel):
        self.travel = travel

    def clone_for_secondary_traveler(self, user_id):
        travel = self._clone_model(self.travel)
        a = 12

    def clone_for_driver(self, user_id):
        pass

    def _clone_model(self, model):
        new_instance = model.__class__.objects.get(pk=model.pk)
        new_instance.pk = None
        new_instance.id = None
        new_instance.save()
        return new_instance