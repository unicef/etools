from __future__ import unicode_literals

from decimal import Decimal as D

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
        permissions = TravelPermission.objects.filter(status=self.travel.status, user_type=self._user_type)
        return {(p.model, p.field, p.permission_type): p.value for p in permissions}

    def has_permission(self, permission_type, model_name, field_name):
        return self._permission_dict.get((permission_type, model_name, field_name), True)


class CostSummaryCalculator(object):
    def __init__(self, travel):
        self.travel = travel

    def calculate_cost_summary(self):
        result = {'dsa_total': self._calculate_dsa_total(),
                  'expenses_total': self._calculate_expenses_total(),
                  'deductions_total': self._calculate_deductions_total()}
        return result

    def _calculate_dsa_total(self):
        return D(0)

    def _calculate_expenses_total(self):
        # TODO: figure out how to handle different currencies
        total = D(0)
        for expense in self.travel.expenses.all():
            total += expense.amount
        return total

    def _calculate_deductions_total(self):
        total = D(0)
        for deduction in self.travel.deductions.all():
            dsa_rate = self._get_dsa_rate_for_date(deduction.date)
            multiplier = self._get_deductiction_multiplier(deduction)
            total += dsa_rate * multiplier
        return total

    def _get_deductiction_multiplier(self, deduction):
        # TODO handle overnight
        multiplier = D(1)

        if deduction.no_dsa:
            multiplier -= D(1)
        if deduction.breakfast:
            multiplier -= D(0.05)
        if deduction.lunch:
            multiplier -= D(0.1)
        if deduction.dinner:
            multiplier -= D(0.15)
        if deduction.accomodation:
            multiplier -= D(0.5)

        # Handle if it goes below zero
        return max(multiplier, 0)

    def _get_dsa_rate_for_date(self, date):
        # TODO implement it
        return D(100)

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