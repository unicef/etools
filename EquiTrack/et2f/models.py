from __future__ import unicode_literals

from datetime import datetime

from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django_fsm import FSMField, transition

from et2f.helpers import CostSummaryCalculator


class UserTypes(object):
    GOD = 'God'
    ANYONE = 'Anyone'
    TRAVELER = 'Traveler'
    TRAVEL_ADMINISTRATOR = 'Travel Administrator'
    SUPERVISOR = 'Supervisor'
    TRAVEL_FOCAL_POINT = 'Travel Focal Point'
    FINANCE_FOCAL_POINT = 'Finance Focal Point'
    REPRESENTATIVE = 'Representative'

    CHOICES = (
        (GOD, 'God'),
        (ANYONE, _('Anyone')),
        (TRAVELER, _('Traveler')),
        (TRAVEL_ADMINISTRATOR, _('Travel Administrator')),
        (SUPERVISOR, _('Supervisor')),
        (TRAVEL_FOCAL_POINT, _('Travel Focal Point')),
        (FINANCE_FOCAL_POINT, _('Finance Focal Point')),
        (REPRESENTATIVE, _('Representative')),
    )


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


class TravelType(models.Model):
    PROGRAMME_MONITORING = 'Programmatic Visit'
    SPOT_CHECK = 'Spot Check'
    ADVOCACY = 'Advocacy'
    TECHNICAL_SUPPORT = 'Technical Support'
    MEETING = 'Meeting'
    STAFF_DEVELOPMENT = 'Staff Development'
    STAFF_ENTITLEMENT = 'Staff Entitlement'
    CHOICES = (
        (PROGRAMME_MONITORING, 'Programmatic Visit'),
        (SPOT_CHECK, 'Spot Check'),
        (ADVOCACY, 'Advocacy'),
        (TECHNICAL_SUPPORT, 'Technical Support'),
        (MEETING, 'Meeting'),
        (STAFF_DEVELOPMENT, 'Staff Development'),
        (STAFF_ENTITLEMENT, 'Staff Entitlement'),
    )

    name = models.CharField(max_length=32, choices=CHOICES)


class ModeOfTravel(models.Model):
    PLANE = 'Plane'
    BUS = 'Bus'
    CAR = 'Car'
    BOAT = 'Boat'
    RAIL = 'Rail'
    CHOICES = (
        (PLANE, 'Plane'),
        (BUS, 'Bus'),
        (CAR, 'Car'),
        (BOAT, 'Boat'),
        (RAIL, 'Rail')
    )
    name = models.CharField(max_length=8, choices=CHOICES)


class Currency(models.Model):
    # This will be populated from vision
    name = models.CharField(max_length=128)
    iso_4217 = models.CharField(max_length=3)


class AirlineCompany(models.Model):
    # This will be populated from vision
    name = models.CharField(max_length=255)
    code = models.IntegerField()
    iata = models.CharField(max_length=3)
    icao = models.CharField(max_length=3)
    country = models.CharField(max_length=255)


class DSARegion(models.Model):
    name = models.CharField(max_length=255)
    dsa_amount_usd = models.DecimalField(max_digits=20, decimal_places=4)
    dsa_amount_60plus_usd = models.DecimalField(max_digits=20, decimal_places=4)
    dsa_amount_local = models.DecimalField(max_digits=20, decimal_places=4)
    dsa_amount_60plus_local = models.DecimalField(max_digits=20, decimal_places=4)
    room_rate = models.DecimalField(max_digits=20, decimal_places=4)


def make_reference_number():
    year = datetime.now().year
    last_travel = Travel.objects.filter(created__year=year).order_by('reference_number').last()
    if last_travel:
        reference_number = last_travel.reference_number
        reference_number = int(reference_number.split('/')[1])
        reference_number += 1
    else:
        reference_number = 1
    return '{}/{:06d}'.format(year, reference_number)


class Travel(models.Model):
    PLANNED = 'planned'
    SUBMITTED = 'submitted'
    REJECTED = 'rejected'
    APPROVED = 'approved'
    CANCELLED = 'cancelled'
    SENT_FOR_PAYMENT = 'sent_for_payment'
    CERTIFICATION_SUBMITTED = 'certification_submitted'
    CERTIFICATION_APPROVED = 'certification_approved'
    CERTIFICATION_REJECTED = 'certification_rejected'
    CERTIFIED = 'certified'
    COMPLETED = 'completed'

    CHOICES = (
        (PLANNED, _('Planned')),
        (SUBMITTED, _('Submitted')),
        (REJECTED, _('Rejected')),
        (APPROVED, _('Approved')),
        (COMPLETED, _('Completed')),
        (CANCELLED, _('Cancelled')),
        (SENT_FOR_PAYMENT, _('Sent for payment')),
        (CERTIFICATION_SUBMITTED, _('Certification submitted')),
        (CERTIFICATION_APPROVED, _('Certification approved')),
        (CERTIFICATION_REJECTED, _('Certification rejected')),
        (CERTIFIED, _('Certified')),
        (COMPLETED, _('Completed')),
    )

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

    status = FSMField(default=PLANNED, choices=CHOICES, protected=True)
    traveler = models.ForeignKey(User, null=True, blank=True, related_name='travels')
    supervisor = models.ForeignKey(User, null=True, blank=True, related_name='+')
    office = models.ForeignKey('users.Office', null=True, blank=True, related_name='+')
    section = models.ForeignKey('users.Section', null=True, blank=True, related_name='+')
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    purpose = models.CharField(max_length=500, null=True, blank=True)
    additional_note = models.TextField(null=True, blank=True)
    international_travel = models.NullBooleanField(default=False, null=True, blank=True)
    ta_required = models.NullBooleanField(default=True, null=True, blank=True)
    reference_number = models.CharField(max_length=12, default=make_reference_number)
    hidden = models.BooleanField(default=False)
    mode_of_travel = models.ManyToManyField('ModeOfTravel', related_name='+')
    estimated_travel_cost = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    currency = models.ForeignKey('Currency', null=True, blank=True, related_name='+')
    is_driver = models.BooleanField(default=False)

    # When the travel is sent for payment, the expenses should be saved for later use
    preserved_expenses = models.DecimalField(max_digits=20, decimal_places=4, null=True, default=None)

    @property
    def approval_date(self):
        return self.approved_at

    @property
    def cost_summary(self):
        calculator = CostSummaryCalculator(self)
        calculator.calculate_cost_summary()
        return calculator.get_cost_summary()

    # State machine transitions
    def check_completion_conditions(self):
        if self.status == Travel.SUBMITTED and not self.international_travel:
            return False
        return True

    @transition(status, source=[PLANNED, REJECTED], target=SUBMITTED)
    def submit_for_approval(self):
        self.send_notification('Travel #{} was sent for approval.'.format(self.id))

    @transition(status, source=[SUBMITTED], target=APPROVED)
    def approve(self):
        self.approved_at = datetime.now()
        self.send_notification('Travel #{} was approved.'.format(self.id))

    @transition(status, source=[SUBMITTED], target=REJECTED)
    def reject(self):
        self.rejected_at = datetime.now()
        self.send_notification('Travel #{} was rejected.'.format(self.id))

    @transition(status, source=[PLANNED,
                                SUBMITTED,
                                REJECTED,
                                APPROVED,
                                SENT_FOR_PAYMENT],
                target=CANCELLED)
    def cancel(self):
        self.canceled_at = datetime.now()

    @transition(status, source=[CANCELLED, REJECTED], target=PLANNED)
    def plan(self):
        pass

    @transition(status, source=[APPROVED], target=SENT_FOR_PAYMENT)
    def send_for_payment(self):
        self.preserved_expenses = self.cost_summary['expenses_total']
        self.send_notification('Travel #{} was sent for payment.'.format(self.id))

    @transition(status, source=[SENT_FOR_PAYMENT, CERTIFICATION_REJECTED],
                target=CERTIFICATION_SUBMITTED)
    def submit_certificate(self):
        self.send_notification('Travel #{} certification was submitted.'.format(self.id))

    @transition(status, source=[CERTIFICATION_SUBMITTED], target=CERTIFICATION_APPROVED)
    def approve_certificate(self):
        self.send_notification('Travel #{} certification was approved.'.format(self.id))

    @transition(status, source=[CERTIFICATION_APPROVED, CERTIFICATION_SUBMITTED],
                target=CERTIFICATION_REJECTED)
    def reject_certificate(self):
        self.send_notification('Travel #{} certification was rejected.'.format(self.id))

    @transition(status, source=[CERTIFICATION_APPROVED, SENT_FOR_PAYMENT],
                target=CERTIFIED)
    def mark_as_certified(self):
        pass

    @transition(status, source=[CERTIFIED, SUBMITTED], target=COMPLETED,
                conditions=[check_completion_conditions])
    def mark_as_completed(self):
        self.completed_at = datetime.now()

    @transition(status, target=PLANNED)
    def reset_status(self):
        pass

    def send_notification(self, message):
        # TODO do this
        pass
        # send_mail('Travel #{} state changed'.format(self.id),
        #           message,
        #           'simon+test@pulilab.com',
        #           ['simon+test@pulilab.com', 'nico+test@pulilab.com'],
        #           fail_silently=False)


class TravelActivity(models.Model):
    travels = models.ManyToManyField('Travel', related_name='activities')
    travel_type = models.ForeignKey('TravelType', related_name='+')
    partner = models.ForeignKey('partners.PartnerOrganization', null=True, related_name='+')
    partnership = models.ForeignKey('partners.PCA', null=True, related_name='+')
    result = models.ForeignKey('reports.Result', null=True, related_name='+')
    locations = models.ManyToManyField('locations.Location', related_name='+')
    primary_traveler = models.BooleanField(default=True)
    date = models.DateTimeField(null=True)


class IteneraryItem(models.Model):
    travel = models.ForeignKey('Travel', related_name='itinerary')
    origin = models.CharField(max_length=255)
    destination = models.CharField(max_length=255)
    departure_date = models.DateTimeField()
    arrival_date = models.DateTimeField()
    dsa_region = models.ForeignKey('DSARegion', related_name='+')
    overnight_travel = models.BooleanField(default=False)
    mode_of_travel = models.ForeignKey('ModeOfTravel', related_name='+')
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
    # TODO: CONFIRM THIS PLEASE
    return 'travels/{}/{}'.format(instance.travel.id, filename)


class TravelAttachment(models.Model):
    travel = models.ForeignKey('Travel', related_name='attachments')
    type = models.CharField(max_length=64)

    name = models.CharField(max_length=255)
    file = models.FileField(upload_to=determine_file_upload_path)


class TravelPermission(models.Model):
    GOD = 'God'
    ANYONE = 'Anyone'
    TRAVELER = 'Traveler'
    TRAVEL_ADMINISTRATOR = 'Travel Administrator'
    SUPERVISOR = 'Supervisor'
    TRAVEL_FOCAL_POINT = 'Travel Focal Point'
    FINANCE_FOCAL_POINT = 'Finance Focal Point'
    REPRESENTATIVE = 'Representative'

    USER_TYPE_CHOICES = (
        (GOD, 'God'),
        (ANYONE, _('Anyone')),
        (TRAVELER, _('Traveler')),
        (TRAVEL_ADMINISTRATOR, _('Travel Administrator')),
        (SUPERVISOR, _('Supervisor')),
        (TRAVEL_FOCAL_POINT, _('Travel Focal Point')),
        (FINANCE_FOCAL_POINT, _('Finance Focal Point')),
        (REPRESENTATIVE, _('Representative')),
    )

    EDIT = 'edit'
    VIEW = 'view'
    PERMISSION_TYPE_CHOICES = (
        (EDIT, 'Edit'),
        (VIEW, 'View'),
    )

    name = models.CharField(max_length=128)
    code = models.CharField(max_length=128)
    status = models.CharField(max_length=50, choices=Travel.CHOICES)
    user_type = models.CharField(max_length=25, choices=USER_TYPE_CHOICES)
    model = models.CharField(max_length=128)
    field = models.CharField(max_length=64)
    permission_type = models.CharField(max_length=5, choices=PERMISSION_TYPE_CHOICES)
    value = models.BooleanField(default=False)
