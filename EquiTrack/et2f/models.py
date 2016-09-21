
from django.db import models
from django.contrib.auth.models import User


class Currency(models.Model):
    name = models.CharField(max_length=128)
    iso_4217 = models.CharField(max_length=3)


class AirlineCompany(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=12)


class Travel(models.Model):
    traveller = models.ForeignKey(User, related_name='travels')
    supervisor = models.ForeignKey(User, related_name='+')
    office = models.ForeignKey('users.Office', related_name='+')
    section = models.ForeignKey('users.Section', related_name='+')
    # start_date = models.DateTimeField()
    # end_date = models.DateTimeField()
    purpose = models.CharField(max_length=120)
    # mode =
    international_travel = models.BooleanField(default=False)
    ta_required = models.BooleanField(default=True)
    reference_number = models.CharField(max_length=12)


class TravelActivity(models.Model):
    travel = models.ForeignKey('Travel', related_name='activities')
    travel_type = models.CharField(max_length=64)
    partner = models.ForeignKey('partners.PartnerOrganization', related_name='+')
    # partnership = models.ForeignKey()
    result = models.ForeignKey('reports.Result', related_name='+')
    location = models.ForeignKey('locations.Location', related_name='+')
    # secondary_traveler = models.BooleanField(default=False)


class IteneraryItem(models.Model):
    travel = models.ForeignKey('Travel', related_name='itinerary')
    origin = models.CharField(max_length=255)
    destination = models.CharField(max_length=255)
    departure_date = models.DateTimeField()
    arrival_date = models.DateTimeField()
    dsa_region = models.CharField(max_length=255)
    overnight_travel = models.BooleanField(default=False)
    mode_of_travel = models.CharField(max_length=255)
    airline = models.ManyToManyField('AirlineCompany')


class Expense(models.Model):
    travel = models.ForeignKey('Travel', related_name='expenses')
    type = models.CharField(max_length=64)
    currency = models.CharField(max_length=3)
    amount = models.DecimalField(max_digits=10, decimal_places=4)


class Deduction(models.Model):
    travel = models.ForeignKey('Travel', related_name='deductions')
    date = models.DateField()
    breakfast = models.BooleanField(default=False)
    lunch = models.BooleanField(default=False)
    dinner = models.BooleanField(default=False)
    accomodation = models.BooleanField(default=False)
    no_dsa = models.BooleanField(default=False)

    @property
    def day_of_the_week(self):
        return 'Mon'


class CostAssignment(models.Model):
    travel = models.ForeignKey('Travel', related_name='cost_assignments')
    # wbs = models.ForeignKey()
    share = models.PositiveIntegerField()
    grant = models.ForeignKey('funds.Grant')
    # fund = models.ForeignKey()


class Clearances(models.Model):
    travel = models.OneToOneField('Travel', related_name='clearances')
    medical_clearance = models.BooleanField(default=False)
    security_clearance = models.BooleanField(default=False)
    security_course = models.BooleanField(default=False)