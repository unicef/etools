from datetime import datetime

from django.contrib.postgres.fields.array import ArrayField
from django.db import models
from django.contrib.auth.models import User
from django_fsm import FSMField, transition

from et2f import BooleanChoice, TripStatus

class Currency(models.Model):
    # This will be populated from vision
    name = models.CharField(max_length=128)
    iso_4217 = models.CharField(max_length=3)


class AirlineCompany(models.Model):
    # This will be populated from vision
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=12)


def make_reference_number():
    return datetime.now().strftime('%H/%M/%S')


class Travel(models.Model):
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    status = FSMField(default=TripStatus.PLANNED, choices=TripStatus.CHOICES, protected=True)
    traveller = models.ForeignKey(User, null=True, blank=True, related_name='travels')
    supervisor = models.ForeignKey(User, null=True, blank=True, related_name='+')
    office = models.ForeignKey('users.Office', null=True, blank=True, related_name='+')
    section = models.ForeignKey('users.Section', null=True, blank=True, related_name='+')
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    purpose = models.CharField(max_length=120, null=True, blank=True)
    international_travel = models.NullBooleanField(default=False, null=True, blank=True)
    ta_required = models.NullBooleanField(default=True, null=True, blank=True)
    reference_number = models.CharField(max_length=12, default=make_reference_number)
    hidden = models.BooleanField(default=False)
    mode_of_travel = ArrayField(models.CharField(max_length=255), default=[])
    estimated_travel_cost = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    currency = models.ForeignKey('Currency', related_name='+')

    @property
    def attachments(self):
        return 0

    @property
    def is_driver(self):
        return False

    @property
    def ta_reference_number(self):
        return ''

    @property
    def approval_date(self):
        return None

    # State machine transitions
    @transition(status, source=[TripStatus.PLANNED, TripStatus.REJECTED], target=TripStatus.SUBMITTED)
    def submit_for_approval(self):
        pass

    @transition(status, source=[TripStatus.SUBMITTED], target=TripStatus.APPROVED)
    def approve(self):
        pass

    @transition(status, source=[TripStatus.SUBMITTED], target=TripStatus.REJECTED)
    def reject(self):
        pass

    @transition(status, source=[TripStatus.PLANNED,


                                TripStatus.REJECTED,
                                TripStatus.APPROVED,
                                TripStatus.SENT_FOR_PAYMENT],
                target=TripStatus.CANCELLED)
    def cancel(self):
        pass

    @transition(status, source=[TripStatus.CANCELLED], target=TripStatus.PLANNED)
    def restore(self):
        pass

    @transition(status, source=[TripStatus.APPROVED], target=TripStatus.SENT_FOR_PAYMENT)
    def send_for_payment(self):
        pass

    @transition(status, source=[TripStatus.SENT_FOR_PAYMENT, TripStatus.APPROVED, TripStatus.CERTIFICATION_REJECTED],
                target=TripStatus.DONE)
    def mark_as_done(self):
        pass

    @transition(status, source=[TripStatus.DONE], target=TripStatus.CERTIFICATION_SUBMITTED)
    def submit_certificate(self):
        pass

    @transition(status, source=[TripStatus.CERTIFICATION_SUBMITTED], target=TripStatus.CERTIFICATION_APPROVED)
    def approve_cetificate(self):
        pass

    @transition(status, source=[TripStatus.CERTIFICATION_APPROVED], target=TripStatus.CERTIFICATION_REJECTED)
    def reject_certificate(self):
        pass

    @transition(status, source=[TripStatus.DONE, TripStatus.CERTIFICATION_APPROVED], target=TripStatus.CERTIFIED)
    def mark_as_certified(self):
        pass

    @transition(status, source=[TripStatus.CERTIFIED], target=TripStatus.COMPLETED)
    def mark_as_completed(self):
        pass


class TravelActivity(models.Model):
    travel = models.ForeignKey('Travel', related_name='activities')
    travel_type = models.CharField(max_length=64)
    partner = models.ForeignKey('partners.PartnerOrganization', related_name='+')
    partnership = models.ForeignKey('partners.PCA', related_name='+')
    result = models.ForeignKey('reports.Result', related_name='+')
    locations = models.ManyToManyField('locations.Location', related_name='+')
    primary_traveler = models.BooleanField(default=True)
    date = models.DateTimeField()


class IteneraryItem(models.Model):
    travel = models.ForeignKey('Travel', related_name='itinerary')
    origin = models.CharField(max_length=255)
    destination = models.CharField(max_length=255)
    departure_date = models.DateTimeField()
    arrival_date = models.DateTimeField()
    dsa_region = models.CharField(max_length=255)
    overnight_travel = models.BooleanField(default=False)
    mode_of_travel = models.CharField(max_length=255)
    airline = models.ForeignKey('AirlineCompany', related_name='+')


class Expense(models.Model):
    travel = models.ForeignKey('Travel', related_name='expenses')
    type = models.CharField(max_length=64)
    document_currency = models.ForeignKey('Currency', related_name='+')
    account_currency = models.ForeignKey('Currency', related_name='+')
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
        return self.date.strftime('%a')


class CostAssignment(models.Model):
    travel = models.ForeignKey('Travel', related_name='cost_assignments')
    wbs = models.ForeignKey('reports.Result', related_name='+')
    share = models.PositiveIntegerField()
    grant = models.ForeignKey('funds.Grant', related_name='+')
    # fund = models.ForeignKey()    # No idea where to connect


class Clearances(models.Model):
    travel = models.OneToOneField('Travel', related_name='clearances')
    medical_clearance = models.NullBooleanField(default=None, choices=BooleanChoice.CHOICES)
    security_clearance = models.NullBooleanField(default=None, choices=BooleanChoice.CHOICES)
    security_course = models.NullBooleanField(default=None, choices=BooleanChoice.CHOICES)