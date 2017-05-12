from __future__ import unicode_literals

from datetime import datetime, timedelta
from decimal import Decimal
from functools import wraps
import logging

from django.contrib.postgres.fields.array import ArrayField
from django.core.exceptions import ValidationError
from django.core.mail.message import EmailMultiAlternatives
from django.contrib.auth.models import User
from django.conf import settings
from django.db import models, connection
from django.template.context import Context
from django.template.loader import render_to_string
from django.utils.timezone import now
from django.utils.translation import ugettext, ugettext_lazy
from django_fsm import FSMField, transition

from publics.models import TravelExpenseType
from t2f.helpers.cost_summary_calculator import CostSummaryCalculator
from t2f.helpers.invoice_maker import InvoiceMaker
from t2f.serializers.mailing import TravelMailSerializer
from users.models import WorkspaceCounter

log = logging.getLogger(__name__)


class TransitionError(RuntimeError):
    """
    Custom exception to send proprer error messages from transitions to the frontend
    """
    pass


class UserTypes(object):

    #TODO: remove God
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
        (ANYONE, ugettext_lazy('Anyone')),
        (TRAVELER, ugettext_lazy('Traveler')),
        (TRAVEL_ADMINISTRATOR, ugettext_lazy('Travel Administrator')),
        (SUPERVISOR, ugettext_lazy('Supervisor')),
        (TRAVEL_FOCAL_POINT, ugettext_lazy('Travel Focal Point')),
        (FINANCE_FOCAL_POINT, ugettext_lazy('Finance Focal Point')),
        (REPRESENTATIVE, ugettext_lazy('Representative')),
    )


class TravelType(object):
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


# TODO: all of these models that only have 1 field should be a choice field on the models that are using it
# for many-to-many array fields are recommended
class ModeOfTravel(object):
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


def make_travel_reference_number():
    numeric_part = connection.tenant.counters.get_next_value(WorkspaceCounter.TRAVEL_REFERENCE)
    year = datetime.now().year
    return '{}/{}'.format(year, numeric_part)


def approve_decorator(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # If invoicing is turned off, jump to sent_for_payment when someone approves the travel
        func(self, *args, **kwargs)

        if settings.DISABLE_INVOICING:
            self.send_for_payment(*args, **kwargs)

    return wrapper


def send_for_payment_threshold_decorator(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # If invoicing is enabled, do the threshold check, otherwise it will result an infinite process loop
        if not settings.DISABLE_INVOICING and self.check_threshold():
            self.submit_for_approval(*args, **kwargs)
            return

        func(self, *args, **kwargs)

    return wrapper


def mark_as_certified_or_completed_threshold_decorator(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # If invoicing is enabled, do the threshold check, otherwise it will result an infinite process loop
        if not settings.DISABLE_INVOICING and self.check_threshold():
            self.submit_certificate(*args, **kwargs)
            return

        func(self, *args, **kwargs)

    return wrapper



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
        (PLANNED, ugettext_lazy('Planned')),
        (SUBMITTED, ugettext_lazy('Submitted')),
        (REJECTED, ugettext_lazy('Rejected')),
        (APPROVED, ugettext_lazy('Approved')),
        (COMPLETED, ugettext_lazy('Completed')),
        (CANCELLED, ugettext_lazy('Cancelled')),
        (SENT_FOR_PAYMENT, ugettext_lazy('Sent for payment')),
        (CERTIFICATION_SUBMITTED, ugettext_lazy('Certification submitted')),
        (CERTIFICATION_APPROVED, ugettext_lazy('Certification approved')),
        (CERTIFICATION_REJECTED, ugettext_lazy('Certification rejected')),
        (CERTIFIED, ugettext_lazy('Certified')),
        (COMPLETED, ugettext_lazy('Completed')),
    )

    created = models.DateTimeField(auto_now_add=True, db_index=True)
    completed_at = models.DateTimeField(null=True)
    canceled_at = models.DateTimeField(null=True)
    submitted_at = models.DateTimeField(null=True)
    # Required to calculate with proper dsa values
    first_submission_date = models.DateTimeField(null=True)
    rejected_at = models.DateTimeField(null=True)
    approved_at = models.DateTimeField(null=True)

    rejection_note = models.TextField(null=True)
    cancellation_note = models.TextField(null=True)
    certification_note = models.TextField(null=True)
    report_note = models.TextField(null=True)
    misc_expenses = models.TextField(null=True)

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
    reference_number = models.CharField(max_length=12, default=make_travel_reference_number, unique=True)
    hidden = models.BooleanField(default=False)
    mode_of_travel = ArrayField(models.CharField(max_length=5, choices=ModeOfTravel.CHOICES), null=True)
    estimated_travel_cost = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    currency = models.ForeignKey('publics.Currency', related_name='+', null=True)
    is_driver = models.BooleanField(default=False)

    # When the travel is sent for payment, the expenses should be saved for later use
    preserved_expenses_local = models.DecimalField(max_digits=20, decimal_places=4, null=True, default=None)
    preserved_expenses_usd = models.DecimalField(max_digits=20, decimal_places=4, null=True, default=None)
    approved_cost_traveler = models.DecimalField(max_digits=20, decimal_places=4, null=True, default=None)
    approved_cost_travel_agencies = models.DecimalField(max_digits=20, decimal_places=4, null=True, default=None)

    def __unicode__(self):
        return self.reference_number

    @property
    def cost_summary(self):
        calculator = CostSummaryCalculator(self)
        return calculator.get_cost_summary()

    def check_threshold(self):
        expenses = {'user': Decimal(0),
                    'travel_agent': Decimal(0)}

        for expense in self.expenses.all():
            if expense.type.vendor_number == TravelExpenseType.USER_VENDOR_NUMBER_PLACEHOLDER:
                expenses['user'] += expense.amount
            else:
                expenses['travel_agent'] += expense.amount

        traveler_delta = 0
        travel_agent_delta = 0
        if self.approved_cost_traveler:
            traveler_delta = expenses['user'] - self.approved_cost_traveler
            if self.currency.code != 'USD':
                exchange_rate = self.currency.exchange_rates.all().last()
                traveler_delta *= exchange_rate.x_rate

        if self.approved_cost_travel_agencies:
            travel_agent_delta = expenses['travel_agent'] - self.approved_cost_travel_agencies

        workspace = self.traveler.profile.country
        if workspace.threshold_tre_usd and traveler_delta > workspace.threshold_tre_usd:
            return True

        if workspace.threshold_tae_usd and travel_agent_delta > workspace.threshold_tae_usd:
            return True

        return False

    # Completion conditions
    def check_trip_report(self):
        if (not self.international_travel) and (self.ta_required) and ((not self.report_note) or
                                                                           (len(self.report_note) < 1)):
            raise TransitionError('Field report has to be filled.')
        return True

    def check_state_flow(self):
        # Complete action should be called only after certification was done.
        # Special case is the TA not required NOT international travel, where supervisor should be able to complete it
        # after approval
        if (self.status == Travel.SUBMITTED) and (self.ta_required) and (not self.international_travel):
            return False

        if (self.status == Travel.PLANNED) and (self.international_travel):
            return False
        return True

    def check_completed_from_planned(self):
        if self.ta_required:
            raise TransitionError('Cannot switch from planned to completed if TA is required')
        return True

    def check_pending_invoices(self):
        # If invoicing is turned off, don't check pending invoices
        if settings.DISABLE_INVOICING:
            return True

        if self.invoices.filter(status__in=[Invoice.PENDING, Invoice.PROCESSING]).exists():
            raise TransitionError('Your TA has pending payments to be processed through VISION. '
                                  'Until payments are completed, you can not certify your TA. '
                                  'Please check with your Finance focal point on how to proceed.')
        return True

    def has_supervisor(self):
        if not self.supervisor:
            raise TransitionError('Travel has no supervisor defined. Please select one.')
        return True

    def check_travel_count(self):
        from t2f.helpers.misc import get_open_travels_for_check
        travels = get_open_travels_for_check(self.traveler)

        if travels.count() >= 3:
            raise TransitionError('Maximum 3 open travels are allowed.')

        end_date_limit = datetime.utcnow() - timedelta(days=15)
        if travels.filter(end_date__lte=end_date_limit).exists():
            raise TransitionError(ugettext('Another of your trips ended more than 15 days ago, but was not completed '
                                           'yet. Please complete that before creating a new trip.'))

        return True

    @transition(status, source=[PLANNED, REJECTED, SENT_FOR_PAYMENT, CANCELLED], target=SUBMITTED,
                conditions=[has_supervisor, check_pending_invoices, check_travel_count])
    def submit_for_approval(self):
        self.submitted_at = now()
        if not self.first_submission_date:
            self.first_submission_date = now()
        self.send_notification_email('Travel #{} was sent for approval.'.format(self.reference_number),
                                     self.supervisor.email,
                                     'emails/submit_for_approval.html')

    @approve_decorator
    @transition(status, source=[SUBMITTED], target=APPROVED)
    def approve(self):
        expenses = {'user': Decimal(0),
                    'travel_agent': Decimal(0)}

        for expense in self.expenses.all():
            if expense.type.vendor_number == TravelExpenseType.USER_VENDOR_NUMBER_PLACEHOLDER:
                expenses['user'] += expense.amount
            elif expense.type.vendor_number:
                expenses['travel_agent'] += expense.amount

        self.approved_cost_traveler = expenses['user']
        self.approved_cost_travel_agencies = expenses['travel_agent']

        self.approved_at = datetime.now()
        self.send_notification_email('Travel #{} was approved.'.format(self.reference_number),
                                     self.traveler.email,
                                     'emails/approved.html')

    @transition(status, source=[SUBMITTED], target=REJECTED)
    def reject(self):
        self.rejected_at = datetime.now()
        self.send_notification_email('Travel #{} was rejected.'.format(self.reference_number),
                                     self.traveler.email,
                                     'emails/rejected.html')

    @transition(status, source=[PLANNED,
                                SUBMITTED,
                                REJECTED,
                                APPROVED,
                                SENT_FOR_PAYMENT,
                                CERTIFIED],
                target=CANCELLED)
    def cancel(self):
        self.canceled_at = datetime.now()
        self.send_notification_email('Travel #{} was cancelled.'.format(self.reference_number),
                                     self.traveler.email,
                                     'emails/cancelled.html')

    @transition(status, source=[CANCELLED, REJECTED], target=PLANNED)
    def plan(self):
        pass

    @send_for_payment_threshold_decorator
    @transition(status, source=[APPROVED, SENT_FOR_PAYMENT, CERTIFIED], target=SENT_FOR_PAYMENT)
    def send_for_payment(self):
        # Expenses total should have at least one element
        if len(self.cost_summary['expenses_total']) == 0:
            raise TransitionError('Travel should have at least one expense.')

        self.preserved_expenses_local = self.cost_summary['expenses_total'][0]['amount']
        self.generate_invoices()

        # If invoicing is turned off, don't send a mail
        if settings.DISABLE_INVOICING:
            return

        self.send_notification_email('Travel #{} sent for payment.'.format(self.reference_number),
                                     self.traveler.email,
                                     'emails/sent_for_payment.html')

    @transition(status, source=[SENT_FOR_PAYMENT, CERTIFICATION_REJECTED, CERTIFIED],
                target=CERTIFICATION_SUBMITTED,
                conditions=[check_pending_invoices])
    def submit_certificate(self):
        self.send_notification_email('Travel #{} certification was submitted.'.format(self.reference_number),
                                     self.supervisor.email,
                                     'emails/certificate_submitted.html')

    @transition(status, source=[CERTIFICATION_SUBMITTED], target=CERTIFICATION_APPROVED)
    def approve_certificate(self):
        self.send_notification_email('Travel #{} certification was approved.'.format(self.reference_number),
                                     self.traveler.email,
                                     'emails/certificate_approved.html')

    @transition(status, source=[CERTIFICATION_APPROVED, CERTIFICATION_SUBMITTED],
                target=CERTIFICATION_REJECTED)
    def reject_certificate(self):
        self.send_notification_email('Travel #{} certification was rejected.'.format(self.reference_number),
                                     self.traveler.email,
                                     'emails/certificate_rejected.html')

    @mark_as_certified_or_completed_threshold_decorator
    @transition(status, source=[CERTIFICATION_APPROVED, SENT_FOR_PAYMENT],
                target=CERTIFIED,
                conditions=[check_pending_invoices])
    def mark_as_certified(self):
        self.generate_invoices()
        self.send_notification_email('Travel #{} certification was certified.'.format(self.reference_number),
                                     self.traveler.email,
                                     'emails/certified.html')

    @mark_as_certified_or_completed_threshold_decorator
    @transition(status, source=[CERTIFIED, SUBMITTED, APPROVED, PLANNED, CANCELLED], target=COMPLETED,
                conditions=[check_trip_report, check_state_flow])
    def mark_as_completed(self):
        self.completed_at = datetime.now()
        self.send_notification_email('Travel #{} was completed.'.format(self.reference_number),
                                     self.supervisor.email,
                                     'emails/trip_completed.html')

        try:
            from partners.models import PartnerOrganization
            for act in self.activities.filter(primary_traveler=self.traveler,
                                              travel_type=TravelType.PROGRAMME_MONITORING,
                                              date__year=datetime.now().year):
                PartnerOrganization.programmatic_visits(act.partner, update_one=True)

            for act in self.activities.filter(primary_traveler=self.traveler,
                                              travel_type=TravelType.SPOT_CHECK,
                                              date__year=datetime.now().year):
                PartnerOrganization.spot_checks(act.partner, update_one=True)
        except Exception as e:
            logging.info('Exception while trying to update hact values {}'.format(e))

    @transition(status, target=PLANNED)
    def reset_status(self):
        pass

    def send_notification_email(self, subject, recipient, template_name):
        # TODO this could be async to avoid too long api calls in case of mail server issue
        serializer = TravelMailSerializer(self, context={})

        url = 'https://{host}/t2f/edit-travel/{travel_id}/'.format(host=settings.HOST,
                                                                   travel_id=self.id)

        context = Context({'travel': serializer.data,
                           'url': url})
        html_content = render_to_string(template_name, context)

        # TODO what should be used?
        sender = settings.DEFAULT_FROM_EMAIL
        msg = EmailMultiAlternatives(subject, '',
                                     sender, [recipient])
        msg.attach_alternative(html_content, 'text/html')

        # Core mailing is broken. Multiple headers will throw an exception
        # https://bugs.python.org/issue28881
        # for filename in ['emails/logo-etools.png', 'emails/logo-unicef.png']:
        #     path = finders.find(filename)
        #     with open(path, 'rb') as fp:
        #         msg_img = MIMEImage(fp.read())
        #
        #     msg_img.add_header('Content-ID', '<{}>'.format(filename))
        #     msg.attach(msg_img)

        try:
            msg.send(fail_silently=False)
        except ValidationError as exc:
            log.error('Was not able to send the email. Exception: %s', exc.message)

    def generate_invoices(self):
        maker = InvoiceMaker(self)
        maker.do_invoicing()


class TravelActivity(models.Model):
    travels = models.ManyToManyField('Travel', related_name='activities')
    travel_type = models.CharField(max_length=64, choices=TravelType.CHOICES, null=True)
    partner = models.ForeignKey('partners.PartnerOrganization', null=True, related_name='+')
    # Partnership has to be filtered based on partner
    # TODO: assert self.partnership.agreement.partner == self.partner
    partnership = models.ForeignKey('partners.Intervention', null=True, related_name='+')
    government_partnership = models.ForeignKey('partners.GovernmentIntervention', null=True, related_name='+')
    result = models.ForeignKey('reports.Result', null=True, related_name='+')
    locations = models.ManyToManyField('locations.Location', related_name='+')
    primary_traveler = models.ForeignKey(User)
    date = models.DateTimeField(null=True)

    @property
    def travel_status(self):
        return self.travels.filter(traveler=self.primary_traveler).first().status


class IteneraryItem(models.Model):
    travel = models.ForeignKey('Travel', related_name='itinerary')
    origin = models.CharField(max_length=255)
    destination = models.CharField(max_length=255)
    departure_date = models.DateTimeField()
    arrival_date = models.DateTimeField()
    dsa_region = models.ForeignKey('publics.DSARegion', related_name='+', null=True)
    overnight_travel = models.BooleanField(default=False)
    mode_of_travel = models.CharField(max_length=5, choices=ModeOfTravel.CHOICES, null=True)
    airlines = models.ManyToManyField('publics.AirlineCompany', related_name='+')

    class Meta:
        # https://docs.djangoproject.com/en/1.9/ref/models/options/#order-with-respect-to
        # see also
        # https://groups.google.com/d/msg/django-users/NQO8OjCHhnA/r9qKklm5y0EJ
        order_with_respect_to = 'travel'

    def __unicode__(self):
        return '{} {} - {}'.format(self.travel.reference_number, self.origin, self.destination)


class Expense(models.Model):
    travel = models.ForeignKey('Travel', related_name='expenses')
    type = models.ForeignKey('publics.TravelExpenseType', related_name='+', null=True)
    currency = models.ForeignKey('publics.Currency', related_name='+', null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=4, null=True)

    @property
    def usd_amount(self):
        if self.currency is None or self.amount is None:
            return None
        xchange_rate = self.currency.exchange_rates.last()
        return self.amount * xchange_rate.x_rate


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

    @property
    def multiplier(self):
        multiplier = Decimal(0)

        if self.no_dsa:
            multiplier += Decimal(1)
        if self.breakfast:
            multiplier += Decimal('0.05')
        if self.lunch:
            multiplier += Decimal('0.1')
        if self.dinner:
            multiplier += Decimal('0.15')
        if self.accomodation:
            multiplier += Decimal('0.5')

        # Handle if it goes above 1
        return min(multiplier, Decimal(1))


class CostAssignment(models.Model):
    travel = models.ForeignKey('Travel', related_name='cost_assignments')
    share = models.PositiveIntegerField()
    delegate = models.BooleanField(default=False)
    business_area = models.ForeignKey('publics.BusinessArea', related_name='+', null=True)
    wbs = models.ForeignKey('publics.WBS', related_name='+', null=True, on_delete=models.DO_NOTHING)
    grant = models.ForeignKey('publics.Grant', related_name='+', null=True, on_delete=models.DO_NOTHING)
    fund = models.ForeignKey('publics.Fund', related_name='+', null=True, on_delete=models.DO_NOTHING)


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
    # TODO: add business area in there
    # return '/'.join(
    #         [connection.schema_name,
    #          'travels',
    #          instance.travel.id,
    #          filename]
    #     )
    country_name = connection.schema_name or 'Uncategorized'
    return 'travels/{}/{}/{}'.format(connection.schema_name, instance.travel.id, filename)


class TravelAttachment(models.Model):
    travel = models.ForeignKey('Travel', related_name='attachments')
    type = models.CharField(max_length=64)

    name = models.CharField(max_length=255)
    file = models.FileField(
        upload_to=determine_file_upload_path,
        max_length=255
    )


class TravelPermission(models.Model):
    EDIT = 'edit'
    VIEW = 'view'
    PERMISSION_TYPE_CHOICES = (
        (EDIT, 'Edit'),
        (VIEW, 'View'),
    )

    TRAVEL = 'travel'
    ACTION_POINT = 'action_point'
    USAGE_PLACE_CHOICES = (
        (TRAVEL, 'Travel'),
        (ACTION_POINT, 'Action point'),
    )

    name = models.CharField(max_length=128)
    code = models.CharField(max_length=128)
    status = models.CharField(max_length=50)
    usage_place = models.CharField(max_length=12, choices=USAGE_PLACE_CHOICES)
    user_type = models.CharField(max_length=25)
    model = models.CharField(max_length=128)
    field = models.CharField(max_length=64)
    permission_type = models.CharField(max_length=5, choices=PERMISSION_TYPE_CHOICES)
    value = models.BooleanField(default=False)


def make_action_point_number():
    year = datetime.now().year
    action_points_qs = ActionPoint.objects.select_for_update().filter(created_at__year=year)

    # This will lock the matching rows and prevent concurency issue
    action_points_qs.values_list('id')

    last_action_point = action_points_qs.order_by('action_point_number').last()
    if last_action_point:
        action_point_number = last_action_point.action_point_number
        action_point_number = int(action_point_number.split('/')[1])
        action_point_number += 1
    else:
        action_point_number = 1
    return '{}/{:06d}'.format(year, action_point_number)


class ActionPoint(models.Model):
    """
    Represents an action point for the trip

    Relates to :model:`trips.Trip`
    Relates to :model:`auth.User`
    """

    OPEN = 'open'
    ONGOING = 'ongoing'
    CANCELLED = 'cancelled'
    COMPLETED = 'completed'

    STATUS = (
        (OPEN, 'Open'),
        (ONGOING, 'Ongoing'),
        (COMPLETED, 'Completed'),
        (CANCELLED, 'Cancelled'),
    )

    travel = models.ForeignKey('Travel', related_name='action_points')
    action_point_number = models.CharField(max_length=11, default=make_action_point_number, unique=True)
    description = models.CharField(max_length=254)
    due_date = models.DateTimeField()
    person_responsible = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+')
    status = models.CharField(choices=STATUS, max_length=254, null=True, verbose_name='Status')
    completed_at = models.DateTimeField(blank=True, null=True)
    actions_taken = models.TextField(blank=True, null=True)
    follow_up = models.BooleanField(default=False)
    comments = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+')

    def save(self, *args, **kwargs):
        if self.status == ActionPoint.OPEN and self.actions_taken:
            self.status = ActionPoint.ONGOING

        if self.status in [ActionPoint.OPEN, ActionPoint.ONGOING] and self.actions_taken and self.completed_at:
            self.status = ActionPoint.COMPLETED

        super(ActionPoint, self).save(*args, **kwargs)


class Invoice(models.Model):
    PENDING = 'pending'
    PROCESSING = 'processing'
    SUCCESS = 'success'
    ERROR = 'error'

    STATUS = (
        (PENDING, 'Pending'),
        (PROCESSING, 'Processing'),
        (SUCCESS, 'Success'),
        (ERROR, 'Error'),
    )

    travel = models.ForeignKey('Travel', related_name='invoices')
    reference_number = models.CharField(max_length=32, unique=True)
    business_area = models.CharField(max_length=32)
    vendor_number = models.CharField(max_length=32)
    currency = models.ForeignKey('publics.Currency', related_name='+', null=True)
    amount = models.DecimalField(max_digits=20, decimal_places=4)
    status = models.CharField(max_length=16, choices=STATUS)
    messages = ArrayField(models.TextField(null=True, blank=True), default=[])
    vision_fi_id = models.CharField(max_length=16, null=True, blank=True)

    def save(self, **kwargs):
        if self.pk is None:
            # This will lock the travel row and prevent concurrency issues
            travel = Travel.objects.select_for_update().get(id=self.travel_id)
            invoice_counter = travel.invoices.all().count() + 1
            self.reference_number = '{}/{}/{:02d}'.format(self.business_area,
                                                          self.travel.reference_number,
                                                          invoice_counter)
        super(Invoice, self).save(**kwargs)

    @property
    def posting_key(self):
        return 'credit' if self.amount >= 0 else 'debit'

    @property
    def normalized_amount(self):
        return abs(self.amount.normalize())

    @property
    def message(self):
        return '\n'.join(self.messages)


class InvoiceItem(models.Model):
    invoice = models.ForeignKey('Invoice', related_name='items')
    wbs = models.ForeignKey('publics.WBS', related_name='+', null=True, on_delete=models.DO_NOTHING)
    grant = models.ForeignKey('publics.Grant', related_name='+', null=True, on_delete=models.DO_NOTHING)
    fund = models.ForeignKey('publics.Fund', related_name='+', null=True, on_delete=models.DO_NOTHING)
    amount = models.DecimalField(max_digits=20, decimal_places=10)

    @property
    def posting_key(self):
        return 'credit' if self.amount >= 0 else 'debit'

    @property
    def normalized_amount(self):
        return abs(self.amount.normalize())
