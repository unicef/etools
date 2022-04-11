import datetime
import logging
from decimal import Decimal

from django.conf import settings
from django.contrib.postgres.fields.array import ArrayField
from django.db import connection, models, transaction
from django.db.models import Case, F, Q, When
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.timezone import now as timezone_now
from django.utils.translation import gettext as _

from django_fsm import FSMField, transition
from unicef_attachments.models import Attachment
from unicef_djangolib.fields import CodedGenericRelation
from unicef_notification.utils import send_notification

from etools.applications.action_points.models import ActionPoint
from etools.applications.core.urlresolvers import build_frontend_url
from etools.applications.t2f.serializers.mailing import TravelMailSerializer
from etools.applications.users.models import WorkspaceCounter

logger = logging.getLogger(__name__)


class TransitionError(RuntimeError):
    """
    Custom exception to send proprer error messages from transitions to the frontend
    """


class TravelType:
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
class ModeOfTravel:
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
    with transaction.atomic():
        numeric_part = connection.tenant.counters.get_next_value(WorkspaceCounter.TRAVEL_REFERENCE)
    year = timezone_now().year
    return '{}/{}'.format(year, numeric_part)


class Travel(models.Model):
    PLANNED = 'planned'
    SUBMITTED = 'submitted'
    REJECTED = 'rejected'
    APPROVED = 'approved'
    CANCELLED = 'cancelled'
    COMPLETED = 'completed'

    CHOICES = (
        (PLANNED, _('Planned')),
        (SUBMITTED, _('Submitted')),
        (REJECTED, _('Rejected')),
        (APPROVED, _('Approved')),
        (COMPLETED, _('Completed')),
        (CANCELLED, _('Cancelled')),
        (COMPLETED, _('Completed')),
    )
    SUBMIT_FOR_APPROVAL = 'submit_for_approval'
    APPROVE = 'approve'
    REJECT = 'reject'
    CANCEL = 'cancel'
    PLAN = 'plan'
    COMPLETE = 'mark_as_completed'

    TRANSACTIONS = (
        SUBMIT_FOR_APPROVAL,
        APPROVE,
        REJECT,
        CANCEL,
        PLAN,
        COMPLETE
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
        verbose_name=_('Traveller'),
        on_delete=models.CASCADE,
    )
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, related_name='+',
        verbose_name=_('Supervisor'),
        on_delete=models.CASCADE,
    )
    office = models.ForeignKey(
        'reports.Office', null=True, blank=True, related_name='+', verbose_name=_('Office'),
        on_delete=models.CASCADE,
    )
    section = models.ForeignKey(
        'reports.Section', null=True, blank=True, related_name='+', verbose_name=_('Section'),
        on_delete=models.CASCADE,
    )
    start_date = models.DateField(null=True, blank=True, verbose_name=_('Start Date'))
    end_date = models.DateField(null=True, blank=True, verbose_name=_('End Date'))
    purpose = models.CharField(max_length=500, default='', blank=True, verbose_name=_('Purpose'))
    additional_note = models.TextField(default='', blank=True, verbose_name=_('Additional Note'))
    international_travel = models.BooleanField(default=False, null=True, blank=True,
                                               verbose_name=_('International Travel'))
    ta_required = models.BooleanField(default=True, null=True, blank=True, verbose_name=_('TA Required'))
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

    # Completion conditions
    def check_trip_report(self):
        if not self.report_note:
            raise TransitionError('Field report has to be filled.')
        return True

    def check_trip_dates(self):
        if self.start_date and self.end_date:
            start_date = self.start_date
            end_date = self.end_date
            travel_q = Q(traveler=self.traveler)
            travel_q &= ~Q(status__in=[Travel.PLANNED, Travel.CANCELLED])
            travel_q &= Q(
                start_date__range=(
                    start_date,
                    end_date - datetime.timedelta(days=1),
                )
            ) | Q(
                end_date__range=(
                    start_date + datetime.timedelta(days=1),
                    end_date,
                )
            )
            travel_q &= ~Q(pk=self.pk)
            if Travel.objects.filter(travel_q).exists():
                raise TransitionError(
                    'You have an existing trip with overlapping dates. '
                    'Please adjust your trip accordingly.'
                )
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

    def has_supervisor(self):
        if not self.supervisor:
            raise TransitionError('Travel has no supervisor defined. Please select one.')
        return True

    def validate_itinerary(self):
        if self.ta_required and self.itinerary.all().count() < 2:
            raise TransitionError(_('Travel must have at least two itinerary item'))

        if self.ta_required and self.itinerary.filter(dsa_region=None).exists():
            raise TransitionError(_('All itinerary items has to have DSA region assigned'))

        return True

    @transition(status, source=[PLANNED, REJECTED, CANCELLED], target=SUBMITTED,
                conditions=[validate_itinerary, has_supervisor])
    def submit_for_approval(self):
        self.submitted_at = timezone_now()
        if not self.first_submission_date:
            self.first_submission_date = timezone_now()
        self.send_notification_email('Travel #{} was sent for approval.'.format(self.reference_number),
                                     self.supervisor.email,
                                     'emails/submit_for_approval.html')

    @transition(status, source=[SUBMITTED], target=APPROVED)
    def approve(self):
        expenses = {'user': Decimal(0),
                    'travel_agent': Decimal(0)}

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

    @transition(status, source=[PLANNED, SUBMITTED, REJECTED, APPROVED],
                target=CANCELLED)
    def cancel(self):
        self.canceled_at = timezone_now()
        recipients = [self.traveler.email]
        if self.status == Travel.APPROVED:
            recipients.append(self.supervisor.email)
        self.send_notification_email('Travel #{} was cancelled.'.format(self.reference_number),
                                     recipients,
                                     'emails/cancelled.html')

    @transition(status, source=[CANCELLED, REJECTED], target=PLANNED)
    def plan(self):
        pass

    @transition(status, source=[SUBMITTED, APPROVED, PLANNED, CANCELLED], target=COMPLETED,
                conditions=[check_trip_report, check_trip_dates, check_state_flow])
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
                if act.partner:
                    act.partner.update_programmatic_visits(event_date=self.end_date, update_one=True)

            for act in self.activities.filter(primary_traveler=self.traveler,
                                              travel_type=TravelType.SPOT_CHECK):
                if act.partner:
                    act.partner.update_spot_checks(event_date=self.end_date, update_one=True)

        except Exception:
            logger.exception('Exception while trying to update hact values.')

    @transition(status, target=PLANNED)
    def reset_status(self):
        pass

    def send_notification_email(self, subject, recipient, template_name):
        # TODO this could be async to avoid too long api calls in case of mail server issue
        serializer = TravelMailSerializer(self, context={})

        recipients = recipient if isinstance(recipient, list) else [recipient]
        send_notification(
            recipients=recipients,
            from_address=settings.DEFAULT_FROM_EMAIL,  # TODO what should sender be?
            subject=subject,
            html_content_filename=template_name,
            context={'travel': serializer.data, 'url': self.get_object_url()}
        )

    def get_object_url(self):
        return build_frontend_url('t2f', 'edit-travel', self.id)


class TravelActivityManager(models.Manager):
    # def get_queryset(self):
    #     return super().get_queryset()
    def annotated_objects(self):
        qs = self.get_queryset()
        qs = qs.annotate(
            primary_ref_number=Case(When(
                travels__traveler=F('primary_traveler'),
                then=F('travels__reference_number')),
                output_field=models.CharField()),
            other_travel_ref_number=F('travels__reference_number'),
            travel_id=Case(When(
                travels__traveler=F('primary_traveler'),
                then=F('travels__pk')),
                output_field=models.CharField()),
        )
        # get all ids of TravelActivity that have at least one matching travel where travels_traveler==primary_traveler
        sub = qs.exclude(travel_id__isnull=True).values_list("id", flat=True)

        # There are the following scenarios:
        # 1. Travel Activity has no travels associated with it, but action points exist related. weird case
        # 2. Travel Activity has one or more travels but none of the travels have TA primary = Trip Traveller
        # 3. Travel Activity has one or more travels and one of them have TA primary = Trip Traveller (traveler match)
        # to cover everything we want to:
        # 1. create a table of TA-Travel (one to one) where we show which TA-Travel combination has a traveler match
        # 2. create a lst of TA ids where we know for a fact that there is one TA-Travel record with traveler match
        # 3. exclude from the table all records without a traveler match that are not in our list
        # The result should be a list of TAs with distinct ids with annotated travel_id when we have traveler match
        return qs.exclude(travel_id__isnull=True, id__in=sub)


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
    date = models.DateField(null=True, blank=True, verbose_name=_('Date'))

    objects = TravelActivityManager()

    class Meta:
        verbose_name_plural = _("Travel Activities")

    @property
    def travel(self):
        return self.travels.filter(traveler=self.primary_traveler).first()

    _reference_number = None

    def get_reference_number(self):
        if self._reference_number:
            return self._reference_number

        travel = self.travels.filter(traveler=self.primary_traveler).first()
        if not travel:
            return

        return travel.reference_number

    def set_reference_number(self, value):
        self._reference_number = value

    reference_number = property(get_reference_number, set_reference_number)

    @property
    def task_number(self):
        return list(self.travel.activities.values_list('id', flat=True)).index(self.id) + 1

    def get_object_url(self):
        travel = self.travels.filter(traveler=self.primary_traveler).first()
        if not travel:
            return

        return travel.get_object_url()

    def __str__(self):
        return '{} - {}'.format(self.travel_type, self.date)


class ItineraryItem(models.Model):
    travel = models.ForeignKey(
        'Travel', related_name='itinerary', verbose_name=_('Travel'),
        on_delete=models.CASCADE,
    )
    origin = models.CharField(max_length=255, verbose_name=_('Origin'))
    destination = models.CharField(max_length=255, verbose_name=_('Destination'))
    departure_date = models.DateField(verbose_name=_('Departure Date'))
    arrival_date = models.DateField(verbose_name=_('Arrival Date'))
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
    file = models.FileField(
        upload_to=determine_file_upload_path,
        max_length=255,
        verbose_name=_('File'),
        blank=True,
        null=True,
    )
    attachment = CodedGenericRelation(
        Attachment,
        verbose_name=_('Travel File'),
        blank=True,
        null=True,
        code='t2f_travel_attachment',
    )


class T2FActionPointManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(travel_activity__isnull=False)


class T2FActionPoint(ActionPoint):
    """
    This proxy class is for easier permissions assigning.
    """
    objects = T2FActionPointManager()

    class Meta(ActionPoint.Meta):
        verbose_name = _('T2F Action Point')
        verbose_name_plural = _('T2F Action Points')
        proxy = True


@receiver(post_save, sender=T2FActionPoint)
def t2f_action_point_updated_receiver(instance, created, **kwargs):
    """TODO User T2FActionPoint to notify users"""
    if created:
        instance.send_email(instance.assigned_to, 't2f/travel_activity/action_point_assigned',
                            cc=[instance.assigned_by.email])
    else:
        if instance.tracker.has_changed('assigned_to'):
            instance.send_email(instance.assigned_to, 't2f/travel_activity/action_point_assigned')
