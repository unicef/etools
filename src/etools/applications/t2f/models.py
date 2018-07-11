import logging
from datetime import timedelta
from decimal import Decimal
from functools import wraps

from django.conf import settings
from django.contrib.postgres.fields.array import ArrayField
from django.db import connection, models
from django.utils.timezone import now as timezone_now
from django.utils.translation import ugettext, ugettext_lazy as _

from django_fsm import FSMField, transition
from unicef_notification.utils import send_notification

from etools.applications.publics.models import TravelExpenseType
from etools.applications.t2f.helpers.cost_summary_calculator import CostSummaryCalculator
from etools.applications.t2f.helpers.invoice_maker import InvoiceMaker
from etools.applications.t2f.serializers.mailing import ActionPointMailSerializer, TravelMailSerializer
from etools.applications.users.models import WorkspaceCounter

log = logging.getLogger(__name__)


class TransitionError(RuntimeError):
    """
    Custom exception to send proprer error messages from transitions to the frontend
    """


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
    year = timezone_now().year
    return '{}/{}'.format(year, numeric_part)


def approve_decorator(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # If invoicing is turned off, jump to sent_for_payment when someone approves the travel
        func(self, *args, **kwargs)

        if settings.DISABLE_INVOICING and self.ta_required:
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

    created = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name=_('Created'))
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Completed At'))
    canceled_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Canceled At'))
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Submitted At'))
    # Required to calculate with proper dsa values
    first_submission_date = models.DateTimeField(null=True, blank=True, verbose_name=_('First Submission Date'))
    rejected_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Rejected At'))
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Approved At'))

    rejection_note = models.TextField(default='', blank=True, verbose_name=_('Rejection Note'))
    cancellation_note = models.TextField(default='', blank=True, verbose_name=_('Cancellation Note'))
    certification_note = models.TextField(default='', blank=True, verbose_name=_('Certification Note'))
    report_note = models.TextField(default='', blank=True, verbose_name=_('Report Note'))
    misc_expenses = models.TextField(default='', blank=True, verbose_name=_('Misc Expenses'))

    status = FSMField(default=PLANNED, choices=CHOICES, protected=True, verbose_name=_('Status'))
    traveler = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, related_name='travels',
        verbose_name=_('Travellert'),
        on_delete=models.CASCADE,
    )
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, related_name='+',
        verbose_name=_('Supervisor'),
        on_delete=models.CASCADE,
    )
    office = models.ForeignKey(
        'users.Office', null=True, blank=True, related_name='+', verbose_name=_('Office'),
        on_delete=models.CASCADE,
    )
    section = models.ForeignKey(
        'reports.Sector', null=True, blank=True, related_name='+', verbose_name=_('Sector'),
        on_delete=models.CASCADE,
    )
    start_date = models.DateTimeField(null=True, blank=True, verbose_name=_('Start Date'))
    end_date = models.DateTimeField(null=True, blank=True, verbose_name=_('End Date'))
    purpose = models.CharField(max_length=500, default='', blank=True, verbose_name=_('Purpose'))
    additional_note = models.TextField(default='', blank=True, verbose_name=_('Additional Note'))
    international_travel = models.NullBooleanField(default=False, null=True, blank=True,
                                                   verbose_name=_('International Travel'))
    ta_required = models.NullBooleanField(default=True, null=True, blank=True, verbose_name=_('TA Required'))
    reference_number = models.CharField(max_length=12, default=make_travel_reference_number, unique=True,
                                        verbose_name=_('Reference Number'))
    hidden = models.BooleanField(default=False, verbose_name=_('Hidden'))
    mode_of_travel = ArrayField(models.CharField(max_length=5, choices=ModeOfTravel.CHOICES), null=True, blank=True,
                                verbose_name=_('Mode of Travel'))
    estimated_travel_cost = models.DecimalField(max_digits=20, decimal_places=4, default=0,
                                                verbose_name=_('Estimated Travel Cost'))
    currency = models.ForeignKey(
        'publics.Currency', related_name='+', null=True, blank=True,
        verbose_name=_('Currency'),
        on_delete=models.CASCADE,
    )
    is_driver = models.BooleanField(default=False, verbose_name=_('Is Driver'))

    # When the travel is sent for payment, the expenses should be saved for later use
    preserved_expenses_local = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True, default=None,
                                                   verbose_name=_('Preserved Expenses (Local)'))
    preserved_expenses_usd = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True, default=None,
                                                 verbose_name=_('Preserved Expenses (USD)'))
    approved_cost_traveler = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True, default=None,
                                                 verbose_name=_('Approved Cost Traveler'))
    approved_cost_travel_agencies = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True,
                                                        default=None, verbose_name=_('Approved Cost Travel Agencies'))

    def __str__(self):
        return self.reference_number

    def get_object_url(self):
        return 'https://{host}/t2f/edit-travel/{travel_id}/'.format(host=settings.HOST,
                                                                    travel_id=self.id)

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
        if not self.report_note:
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
        if settings.DISABLE_INVOICING and self.ta_required:
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
        from etools.applications.t2f.helpers.misc import get_open_travels_for_check
        travels = get_open_travels_for_check(self.traveler)

        if travels.count() >= 3:
            raise TransitionError('Maximum 3 open travels are allowed.')

        end_date_limit = timezone_now() - timedelta(days=15)
        if travels.filter(end_date__lte=end_date_limit).exclude(id=self.id).exists():
            raise TransitionError(ugettext('Another of your trips ended more than 15 days ago, but was not completed '
                                           'yet. Please complete that before creating a new trip.'))

        return True

    def validate_itinerary(self):
        if self.ta_required and self.itinerary.all().count() < 2:
            raise TransitionError(ugettext('Travel must have at least two itinerary item'))

        if self.ta_required and self.itinerary.filter(dsa_region=None).exists():
            raise TransitionError(ugettext('All itinerary items has to have DSA region assigned'))

        return True

    @transition(status, source=[PLANNED, REJECTED, SENT_FOR_PAYMENT, CANCELLED], target=SUBMITTED,
                conditions=[validate_itinerary, has_supervisor, check_pending_invoices, check_travel_count])
    def submit_for_approval(self):
        self.submitted_at = timezone_now()
        if not self.first_submission_date:
            self.first_submission_date = timezone_now()
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

        self.approved_at = timezone_now()
        self.send_notification_email('Travel #{} was approved.'.format(self.reference_number),
                                     self.traveler.email,
                                     'emails/approved.html')

    @transition(status, source=[SUBMITTED], target=REJECTED)
    def reject(self):
        self.rejected_at = timezone_now()
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
        self.canceled_at = timezone_now()
        self.send_notification_email('Travel #{} was cancelled.'.format(self.reference_number),
                                     self.traveler.email,
                                     'emails/cancelled.html')

    @transition(status, source=[CANCELLED, REJECTED], target=PLANNED)
    def plan(self):
        pass

    @send_for_payment_threshold_decorator
    @transition(status, source=[APPROVED, SENT_FOR_PAYMENT, CERTIFIED], target=SENT_FOR_PAYMENT)
    def send_for_payment(self):
        if self.cost_summary['expenses_total']:
            self.preserved_expenses_local = self.cost_summary['expenses_total'][0]['amount']
        else:
            self.preserved_expenses_local = Decimal(0)
        self.generate_invoices()

        # If invoicing is turned off, don't send a mail
        if settings.DISABLE_INVOICING and self.ta_required:
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
        self.completed_at = timezone_now()
        if not self.ta_required and self.status == self.PLANNED:
            self.send_notification_email('Travel #{} was completed.'.format(self.reference_number),
                                         self.supervisor.email,
                                         'emails/no_approval_complete.html')
        else:
            self.send_notification_email('Travel #{} was completed.'.format(self.reference_number),
                                         self.supervisor.email,
                                         'emails/trip_completed.html')

        try:
            for act in self.activities.filter(primary_traveler=self.traveler,
                                              travel_type=TravelType.PROGRAMME_MONITORING):
                act.partner.programmatic_visits(event_date=self.end_date, update_one=True)

            for act in self.activities.filter(primary_traveler=self.traveler,
                                              travel_type=TravelType.SPOT_CHECK):
                act.partner.spot_checks(event_date=self.end_date, update_one=True)

        except Exception:
            log.exception('Exception while trying to update hact values.')

    @transition(status, target=PLANNED)
    def reset_status(self):
        pass

    def send_notification_email(self, subject, recipient, template_name):
        # TODO this could be async to avoid too long api calls in case of mail server issue
        serializer = TravelMailSerializer(self, context={})

        send_notification(
            recipients=[recipient],
            from_address=settings.DEFAULT_FROM_EMAIL,  # TODO what should sender be?
            subject=subject,
            html_content_filename=template_name,
            context={'travel': serializer.data, 'url': self.get_object_url()}
        )

    def generate_invoices(self):
        maker = InvoiceMaker(self)
        maker.do_invoicing()


class TravelActivity(models.Model):
    travels = models.ManyToManyField('Travel', related_name='activities', verbose_name=_('Travels'))
    travel_type = models.CharField(max_length=64, choices=TravelType.CHOICES, blank=True,
                                   default=TravelType.PROGRAMME_MONITORING,
                                   verbose_name=_('Travel Type'))
    partner = models.ForeignKey(
        'partners.PartnerOrganization', null=True, blank=True, related_name='+',
        verbose_name=_('Partner'),
        on_delete=models.CASCADE,
    )
    # Partnership has to be filtered based on partner
    # TODO: assert self.partnership.agreement.partner == self.partner
    partnership = models.ForeignKey(
        'partners.Intervention', null=True, blank=True, related_name='travel_activities',
        verbose_name=_('Partnership'),
        on_delete=models.CASCADE,
    )
    result = models.ForeignKey(
        'reports.Result', null=True, blank=True, related_name='+', verbose_name=_('Result'),
        on_delete=models.CASCADE,
    )
    locations = models.ManyToManyField('locations.Location', related_name='+', verbose_name=_('Locations'))
    primary_traveler = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_('Primary Traveler'), on_delete=models.CASCADE)
    date = models.DateTimeField(null=True, blank=True, verbose_name=_('Date'))

    class Meta:
        verbose_name_plural = _("Travel Activities")

    @property
    def travel_status(self):
        return self.travels.filter(traveler=self.primary_traveler).first().status


class ItineraryItem(models.Model):
    travel = models.ForeignKey(
        'Travel', related_name='itinerary', verbose_name=_('Travel'),
        on_delete=models.CASCADE,
    )
    origin = models.CharField(max_length=255, verbose_name=_('Origin'))
    destination = models.CharField(max_length=255, verbose_name=_('Destination'))
    departure_date = models.DateTimeField(verbose_name=_('Departure Date'))
    arrival_date = models.DateTimeField(verbose_name=_('Arrival Date'))
    dsa_region = models.ForeignKey(
        'publics.DSARegion', related_name='+', null=True, blank=True,
        verbose_name=_('DSA Region'),
        on_delete=models.CASCADE,
    )
    overnight_travel = models.BooleanField(default=False, verbose_name=_('Overnight Travel'))
    mode_of_travel = models.CharField(max_length=5, choices=ModeOfTravel.CHOICES, default='', blank=True,
                                      verbose_name=_('Mode of Travel'))
    airlines = models.ManyToManyField('publics.AirlineCompany', related_name='+', verbose_name=_('Airlines'))

    class Meta:
        # https://docs.djangoproject.com/en/1.9/ref/models/options/#order-with-respect-to
        # see also
        # https://groups.google.com/d/msg/django-users/NQO8OjCHhnA/r9qKklm5y0EJ
        order_with_respect_to = 'travel'

    def __str__(self):
        return '{} {} - {}'.format(self.travel.reference_number, self.origin, self.destination)


class Expense(models.Model):
    travel = models.ForeignKey(
        'Travel', related_name='expenses', verbose_name=_('Travel'),
        on_delete=models.CASCADE,
    )
    type = models.ForeignKey(
        'publics.TravelExpenseType', related_name='+', null=True, blank=True,
        verbose_name=_('Type'),
        on_delete=models.CASCADE,
    )
    currency = models.ForeignKey(
        'publics.Currency', related_name='+', null=True, blank=True,
        verbose_name=_('Currency'),
        on_delete=models.CASCADE,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, verbose_name=_('Amount'))

    @property
    def usd_amount(self):
        if self.currency is None or self.amount is None:
            return None
        xchange_rate = self.currency.exchange_rates.last()
        return self.amount * xchange_rate.x_rate


class Deduction(models.Model):
    travel = models.ForeignKey(
        'Travel', related_name='deductions', verbose_name=_('Deduction'),
        on_delete=models.CASCADE,
    )
    date = models.DateField(verbose_name=_('Date'))
    breakfast = models.BooleanField(default=False, verbose_name=_('Breakfast'))
    lunch = models.BooleanField(default=False, verbose_name=_('Lunch'))
    dinner = models.BooleanField(default=False, verbose_name=_('Dinner'))
    accomodation = models.BooleanField(default=False, verbose_name=_('Accomodation'))
    no_dsa = models.BooleanField(default=False, verbose_name=_('No DSA'))

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
    travel = models.ForeignKey(
        'Travel', related_name='cost_assignments', verbose_name=_('Travel'),
        on_delete=models.CASCADE,
    )
    share = models.PositiveIntegerField(verbose_name=_('Share'))
    delegate = models.BooleanField(default=False, verbose_name=_('Delegate'))
    business_area = models.ForeignKey(
        'publics.BusinessArea', related_name='+', null=True, blank=True,
        verbose_name=_('Business Area'),
        on_delete=models.CASCADE,
    )
    wbs = models.ForeignKey('publics.WBS', related_name='+', null=True, blank=True, on_delete=models.DO_NOTHING,
                            verbose_name=_('WBS'))
    grant = models.ForeignKey('publics.Grant', related_name='+', null=True, blank=True, on_delete=models.DO_NOTHING,
                              verbose_name=_('Grant'))
    fund = models.ForeignKey('publics.Fund', related_name='+', null=True, blank=True, on_delete=models.DO_NOTHING,
                             verbose_name=_('Fund'))


class Clearances(models.Model):
    REQUESTED = 'requested'
    NOT_REQUESTED = 'not_requested'
    NOT_APPLICABLE = 'not_applicable'
    CHOICES = (
        (REQUESTED, 'requested'),
        (NOT_REQUESTED, 'not_requested'),
        (NOT_APPLICABLE, 'not_applicable'),
    )

    travel = models.OneToOneField('Travel', related_name='clearances', verbose_name=_('Travel'),
                                  on_delete=models.CASCADE)
    medical_clearance = models.CharField(max_length=14, choices=CHOICES, default=NOT_APPLICABLE,
                                         verbose_name=_('Medical Clearance'))
    security_clearance = models.CharField(max_length=14, choices=CHOICES, default=NOT_APPLICABLE,
                                          verbose_name=_('Security Clearance'))
    security_course = models.CharField(max_length=14, choices=CHOICES, default=NOT_APPLICABLE,
                                       verbose_name=_('Security Course'))

    class Meta:
        verbose_name_plural = _('Clearances')


def determine_file_upload_path(instance, filename):
    # TODO: add business area in there
    country_name = connection.schema_name or 'Uncategorized'
    return 'travels/{}/{}/{}'.format(country_name, instance.travel.id, filename)


class TravelAttachment(models.Model):
    travel = models.ForeignKey(
        'Travel', related_name='attachments', verbose_name=_('Travel'),
        on_delete=models.CASCADE,
    )
    type = models.CharField(max_length=64, verbose_name=_('Type'))

    name = models.CharField(max_length=255, verbose_name=_('Name'))
    file = models.FileField(upload_to=determine_file_upload_path, max_length=255, verbose_name=_('File'))


def make_action_point_number():
    year = timezone_now().year
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

    Relates to :model:`Travel`
    Relates to :model:`AUTH_USER_MODEL`
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

    travel = models.ForeignKey(
        'Travel', related_name='action_points', verbose_name=_('Travel'),
        on_delete=models.CASCADE,
    )
    action_point_number = models.CharField(max_length=11, default=make_action_point_number, unique=True,
                                           verbose_name=_('Action Point Number'))
    description = models.CharField(max_length=254, verbose_name=_('Description'))
    due_date = models.DateTimeField(verbose_name=_('Due Date'))
    person_responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='+',
        verbose_name=_('Responsible Person'),
        on_delete=models.CASCADE,
    )
    status = models.CharField(choices=STATUS, max_length=254, default='', blank=True, verbose_name='Status')
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name=_('Completed At'))
    actions_taken = models.TextField(blank=True, default='', verbose_name=_('Actions Taken'))
    follow_up = models.BooleanField(default=False, verbose_name=_('Follow up'))
    comments = models.TextField(blank=True, default='', verbose_name=_('Comments'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='+', verbose_name=_('Assigned By'),
        on_delete=models.CASCADE,
    )

    def save(self, *args, **kwargs):
        created = self.pk is None

        if self.status == ActionPoint.OPEN and self.actions_taken:
            self.status = ActionPoint.ONGOING

        if self.status in [ActionPoint.OPEN, ActionPoint.ONGOING] and self.actions_taken and self.completed_at:
            self.status = ActionPoint.COMPLETED

        super(ActionPoint, self).save(*args, **kwargs)

        if created:
            self.send_notification_email()

    def send_notification_email(self):
        # TODO this could be async to avoid too long api calls in case of mail server issue
        serializer = ActionPointMailSerializer(self, context={})

        recipient = self.person_responsible.email
        cc = self.assigned_by.email
        subject = '[eTools] ACTION POINT ASSIGNED to {}'.format(self.person_responsible)
        url = 'https://{host}/t2f/action-point/{action_point_id}/'.format(host=settings.HOST,
                                                                          action_point_id=self.id)
        trip_url = 'https://{host}/t2f/edit-travel/{travel_id}'.format(host=settings.HOST, travel_id=self.travel.id)

        context = {'action_point': serializer.data, 'url': url, 'trip_url': trip_url}
        template_name = 'emails/action_point_assigned.html'

        send_notification(
            recipients=[recipient],
            cc=[cc],
            from_address=settings.DEFAULT_FROM_EMAIL,  # TODO what should sender be?
            subject=subject,
            html_content_filename=template_name,
            content='',
            context=context,
        )


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

    travel = models.ForeignKey(
        'Travel', related_name='invoices', verbose_name=_('Travel'),
        on_delete=models.CASCADE,
    )
    reference_number = models.CharField(max_length=32, unique=True, verbose_name=_('Reference Number'))
    business_area = models.CharField(max_length=32, verbose_name=_('Business Area'))
    vendor_number = models.CharField(max_length=32, verbose_name=_('Vendor Number'))
    currency = models.ForeignKey(
        'publics.Currency', related_name='+', verbose_name=_('Currency'),
        on_delete=models.CASCADE,
    )
    amount = models.DecimalField(max_digits=20, decimal_places=4, verbose_name=_('Amount'))
    status = models.CharField(max_length=16, choices=STATUS, verbose_name=_('Status'))
    messages = ArrayField(models.TextField(default='', blank=True), default=[], verbose_name=_('Messages'))
    vision_fi_id = models.CharField(max_length=16, default='', blank=True, verbose_name=_('Vision FI ID'))

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

    def __str__(self):
        return self.reference_number

    class Meta:
        ordering = ["pk", ]


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(
        'Invoice', related_name='items', verbose_name=_('Invoice'),
        on_delete=models.CASCADE,
    )
    wbs = models.ForeignKey('publics.WBS', related_name='+', null=True, blank=True, on_delete=models.DO_NOTHING,
                            verbose_name=_(''))
    grant = models.ForeignKey('publics.Grant', related_name='+', null=True, blank=True, on_delete=models.DO_NOTHING,
                              verbose_name=_('Grant'))
    fund = models.ForeignKey('publics.Fund', related_name='+', null=True, blank=True, on_delete=models.DO_NOTHING,
                             verbose_name=_('Fund'))
    amount = models.DecimalField(max_digits=20, decimal_places=10)

    @property
    def posting_key(self):
        return 'credit' if self.amount >= 0 else 'debit'

    @property
    def normalized_amount(self):
        return abs(self.amount.normalize())
