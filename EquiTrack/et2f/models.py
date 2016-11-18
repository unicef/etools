from __future__ import unicode_literals

from datetime import datetime

from django.core.mail import send_mail
from django.contrib.postgres.fields.array import ArrayField
from django.core.urlresolvers import reverse
from django.db import models
from django.contrib.auth.models import User
from django_fsm import FSMField, transition

from et2f import BooleanChoice, TripStatus, UserTypes
from et2f.helpers import CostSummaryCalculator


class WBS(models.Model):
    name = models.CharField(max_length=25)

class Grant(models.Model):
    wbs = models.ForeignKey('WBS', related_name='grants')
    name = models.CharField(max_length=25)

class Fund(models.Model):
    grant = models.ForeignKey('Grant', related_name='funds')
    name = models.CharField(max_length=25)


class ExpenseType(models.Model):
    title = models.CharField(max_length=32)
    code = models.CharField(max_length=16)


class TravelPermission(models.Model):
    EDIT = 'edit'
    VIEW = 'view'
    CHOICES = (
        (EDIT, 'Edit'),
        (VIEW, 'View'),
    )

    name = models.CharField(max_length=128)
    code = models.CharField(max_length=128)
    status = models.CharField(max_length=50, choices=TripStatus.CHOICES)
    user_type = models.CharField(max_length=25, choices=UserTypes.CHOICES)
    model = models.CharField(max_length=128)
    field = models.CharField(max_length=64)
    permission_type = models.CharField(max_length=5, choices=CHOICES)
    value = models.BooleanField(default=False)


class Currency(models.Model):
    # This will be populated from vision
    name = models.CharField(max_length=128)
    iso_4217 = models.CharField(max_length=3)


class AirlineCompany(models.Model):
    # This will be populated from vision
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=12)


class DSARegion(models.Model):
    name = models.CharField(max_length=255)
    dsa_amount_usd = models.DecimalField(max_digits=20, decimal_places=4)
    dsa_amount_60plus_usd = models.DecimalField(max_digits=20, decimal_places=4)
    dsa_amount_local = models.DecimalField(max_digits=20, decimal_places=4)
    dsa_amount_60plus_local = models.DecimalField(max_digits=20, decimal_places=4)
    room_rate = models.DecimalField(max_digits=20, decimal_places=4)


def make_reference_number():
    return datetime.now().strftime('%H/%M/%S')


class Travel(models.Model):
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    completed_at = models.DateTimeField(null=True)
    canceled_at = models.DateTimeField(null=True)
    submitted_at = models.DateTimeField(null=True)
    rejected_at = models.DateTimeField(null=True)
    approved_at = models.DateTimeField(null=True)

    rejection_note = models.TextField(null=True)
    cancellation_note = models.TextField(null=True)
    certification_note = models.TextField(null=True)
    report_note = models.TextField(null=True)

    status = FSMField(default=TripStatus.PLANNED, choices=TripStatus.CHOICES, protected=True)
    traveller = models.ForeignKey(User, null=True, blank=True, related_name='travels')
    supervisor = models.ForeignKey(User, null=True, blank=True, related_name='+')
    office = models.ForeignKey('users.Office', null=True, blank=True, related_name='+')
    section = models.ForeignKey('users.Section', null=True, blank=True, related_name='+')
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    purpose = models.CharField(max_length=500, null=True, blank=True)
    international_travel = models.NullBooleanField(default=False, null=True, blank=True)
    ta_required = models.NullBooleanField(default=True, null=True, blank=True)
    reference_number = models.CharField(max_length=12, default=make_reference_number)
    hidden = models.BooleanField(default=False)
    mode_of_travel = ArrayField(models.CharField(max_length=255), default=[])
    estimated_travel_cost = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    currency = models.ForeignKey('Currency', null=True, blank=True, related_name='+')

    @property
    def is_driver(self):
        return False

    @property
    def ta_reference_number(self):
        return ''

    @property
    def approval_date(self):
        return self.approved_at

    @property
    def cost_summary(self):
        calculator = CostSummaryCalculator(self)
        return calculator.calculate_cost_summary()

    # State machine transitions
    @transition(status, source=[TripStatus.PLANNED, TripStatus.REJECTED], target=TripStatus.SUBMITTED)
    def submit_for_approval(self):
        self.send_notification('Travel #{} was sent for approval.'.format(self.id))

    @transition(status, source=[TripStatus.SUBMITTED], target=TripStatus.APPROVED)
    def approve(self):
        self.approved_at = datetime.now()
        self.send_notification('Travel #{} was approved.'.format(self.id))

    @transition(status, source=[TripStatus.SUBMITTED], target=TripStatus.REJECTED)
    def reject(self):
        self.rejected_at = datetime.now()
        self.send_notification('Travel #{} was rejected.'.format(self.id))

    @transition(status, source=[TripStatus.PLANNED,


                                TripStatus.REJECTED,
                                TripStatus.APPROVED,
                                TripStatus.SENT_FOR_PAYMENT],
                target=TripStatus.CANCELLED)
    def cancel(self):
        self.canceled_at = datetime.now()

    @transition(status, source=[TripStatus.CANCELLED, TripStatus.REJECTED], target=TripStatus.PLANNED)
    def plan(self):
        pass

    @transition(status, source=[TripStatus.APPROVED], target=TripStatus.SENT_FOR_PAYMENT)
    def send_for_payment(self):
        self.send_notification('Travel #{} was sent for payment.'.format(self.id))

    @transition(status, source=[TripStatus.DONE, TripStatus.SENT_FOR_PAYMENT],
                target=TripStatus.CERTIFICATION_SUBMITTED)
    def submit_certificate(self):
        self.send_notification('Travel #{} certification was submitted.'.format(self.id))

    @transition(status, source=[TripStatus.CERTIFICATION_SUBMITTED], target=TripStatus.CERTIFICATION_APPROVED)
    def approve_cetificate(self):
        self.send_notification('Travel #{} certification was approved.'.format(self.id))

    @transition(status, source=[TripStatus.CERTIFICATION_APPROVED], target=TripStatus.CERTIFICATION_REJECTED)
    def reject_certificate(self):
        self.send_notification('Travel #{} certification was rejected.'.format(self.id))

    @transition(status, source=[TripStatus.DONE, TripStatus.CERTIFICATION_APPROVED, TripStatus.SENT_FOR_PAYMENT],
                target=TripStatus.CERTIFIED)
    def mark_as_certified(self):
        pass

    @transition(status, source=[TripStatus.CERTIFIED], target=TripStatus.COMPLETED)
    def mark_as_completed(self):
        self.completed_at = datetime.now()

    @transition(status, target=TripStatus.PLANNED)
    def reset_status(self):
        pass

    def send_notification(self, message):
        send_mail('Travel #{} state changed'.format(self.id),
                  message,
                  'simon+test@pulilab.com',
                  ['simon+test@pulilab.com', 'nico+test@pulilab.com'],
                  fail_silently=False)


class TravelActivity(models.Model):
    travels = models.ManyToManyField('Travel', related_name='activities')
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
    dsa_region = models.ForeignKey('DSARegion', related_name='+')
    overnight_travel = models.BooleanField(default=False)
    mode_of_travel = models.CharField(max_length=255)
    airlines = models.ManyToManyField('AirlineCompany', related_name='+')


class Expense(models.Model):
    travel = models.ForeignKey('Travel', related_name='expenses')
    type = models.ForeignKey('ExpenseType', related_name='+')
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
    share = models.PositiveIntegerField()
    wbs = models.ForeignKey('WBS', related_name='+')
    grant = models.ForeignKey('Grant', related_name='+')
    fund = models.ForeignKey('Fund', related_name='+')


class Clearances(models.Model):
    REQUESTED = 'requested'
    NOT_REQUESTED = 'not_requested'
    NOT_APPLICABLE = 'not_applicable'
    CHOICES = (
        (REQUESTED, 'requested'),
        (NOT_REQUESTED, 'not_requested'),
        (NOT_APPLICABLE, 'not_applicable'),
    )

    travel = models.OneToOneField('Travel', related_name='clearances')
    medical_clearance = models.CharField(max_length=14, choices=CHOICES, default=NOT_APPLICABLE)
    security_clearance = models.CharField(max_length=14, choices=CHOICES, default=NOT_APPLICABLE)
    security_course = models.CharField(max_length=14, choices=CHOICES, default=NOT_APPLICABLE)


def determine_file_upload_path(instance, filename):
    # CONFIRM THIS PLEASE
    return 'travels/{}/{}'.format(instance.travel.id, filename)


class TravelAttachment(models.Model):
    travel = models.ForeignKey('Travel', related_name='attachments')
    type = models.CharField(max_length=64)

    name = models.CharField(max_length=255)
    file = models.FileField(upload_to=determine_file_upload_path)