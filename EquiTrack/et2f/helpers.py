from __future__ import unicode_literals

from datetime import timedelta
from decimal import Decimal

from django.utils.functional import cached_property

from django.core.exceptions import ObjectDoesNotExist


class PermissionMatrix(object):
    def __init__(self, travel, user):
        self.travel = travel
        self.user = user
        self._user_type = self.get_user_type()
        self._permission_dict = self.get_permission_dict()

    def get_user_type(self):
        from et2f.models import UserTypes
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
        self._calculated = False

    def _init_values(self):
        self._dsa_data = []
        self._dsa_total = Decimal(0)
        self._total_deductions = Decimal(0)
        self._total_expenses = Decimal(0)

    @cached_property
    def _deductions(self):
        return {d.date: d for d in self.travel.deductions.all()}

    def get_cost_summary(self):
        result = {'dsa_total': self._dsa_total.quantize(Decimal('1.0000')),
                  'expenses_total': self._total_expenses.quantize(Decimal('1.0000')),
                  'deductions_total': self._total_deductions.quantize(Decimal('1.0000')),
                  'dsa': self._dsa_data,
                  'preserved_expenses': self.travel.preserved_expenses}
        return result

    def calculate_cost_summary(self):
        self._init_values()
        self._total_expenses = self._calculate_total_expenses()

        itinerary_items_list = list(self.travel.itinerary.order_by('departure_date'))

        if not itinerary_items_list:
            return 

        # All but last travel
        for item_id, itinerary_item in enumerate(itinerary_items_list[:-1]):
            start_date = itinerary_item.departure_date.date()
            end_date = itinerary_items_list[item_id+1].departure_date.date()
            self._calculate_dsa_rate_for_timeframe(itinerary_item, start_date, end_date)

        # Last travel
        itinerary_item = itinerary_items_list[-1]
        start_date = itinerary_item.departure_date.date()
        # +1 day because of the < comparison
        end_date = itinerary_item.arrival_date.date()
        self._calculate_dsa_rate_for_timeframe(itinerary_item, start_date, end_date, True)

    def _calculate_dsa_rate_for_timeframe(self, itinerary_item, start_date, end_date, count_last_day=False):
        delta_day = timedelta(days=1)
        dsa_region = itinerary_item.dsa_region

        dsa = {'start_date': start_date,
               'end_date': end_date,
               'dsa_region': dsa_region.id,
               'dsa_region_name': dsa_region.name}

        if count_last_day:
            end_date += delta_day

        night_count = Decimal((end_date - start_date).days)
        dsa['night_count'] = night_count

        total_amount_usd = Decimal(0)
        current_day = start_date
        day_count = 1
        while current_day < end_date:
            last_day = (current_day+delta_day) >= end_date

            if day_count <= 60:
                daily_rate = dsa_region.dsa_amount_usd
            else:
                daily_rate = dsa_region.dsa_amount_60plus_usd

            if count_last_day and last_day:
                deduction_multiplier = Decimal('0.6')
            else:
                if itinerary_item.overnight_travel and current_day <= itinerary_item.departure_date.date():
                    overnight_travel = True
                else:
                    overnight_travel = False
                deduction_multiplier = self._get_deduction_multiplier_at(current_day, overnight_travel)

            deduction = daily_rate * deduction_multiplier
            daily_rate -= deduction

            total_amount_usd += daily_rate
            if not count_last_day and not last_day:
                self._total_deductions += deduction

            current_day += delta_day
            day_count += 1

        if night_count:
            daily_rate_usd = total_amount_usd / night_count
        else:
            daily_rate_usd = total_amount_usd

        dsa['daily_rate_usd'] = daily_rate_usd.quantize(Decimal('1.0000'))
        dsa['amount_usd'] = total_amount_usd.quantize(Decimal('1.0000'))
        self._dsa_data.append(dsa)
        self._dsa_total += total_amount_usd

    def _calculate_total_expenses(self):
        # TODO: DB sum should be used
        total = Decimal(0)
        for expense in self.travel.expenses.all():
            total += expense.amount
        return total

    def _get_deduction_multiplier_at(self, date, overnight_travel=False):
        multiplier = Decimal(0)

        try:
            deduction = self._deductions[date]
        except KeyError:
            return multiplier

        if deduction.no_dsa:
            multiplier += Decimal(1)
        if deduction.breakfast:
            multiplier += Decimal('0.05')
        if deduction.lunch:
            multiplier += Decimal('0.1')
        if deduction.dinner:
            multiplier += Decimal('0.15')
        if deduction.accomodation:
            multiplier += Decimal('0.5')
        if overnight_travel:
            multiplier += Decimal(1)

        # Handle if it goes above 1
        return min(multiplier, Decimal(1))


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
        new_instance = model.__class__.objects.get(pk=model.pk)
        new_instance.pk = None
        new_instance.id = None
        return new_instance
