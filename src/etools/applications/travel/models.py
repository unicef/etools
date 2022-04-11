from django.conf import settings
from django.db import connection, models, transaction
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from django_fsm import FSMField, transition
from model_utils import Choices
from model_utils.models import TimeStampedModel
from unicef_attachments.models import Attachment
from unicef_djangolib.fields import CodedGenericRelation

from etools.applications.core.permissions import import_permissions
from etools.applications.core.urlresolvers import build_frontend_url
from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.locations.models import Location
from etools.applications.partners.models import PartnerOrganization
from etools.applications.reports.models import Office, Section
from etools.applications.travel.validation import (
    trip_approved,
    trip_illegal_transition,
    trip_rejected,
    trip_submitted,
    trip_subreview,
)


class Trip(TimeStampedModel):
    STATUS_DRAFT = 'draft'
    STATUS_SUBMISSION_REVIEW = 'submission'
    STATUS_SUBMITTED = 'submitted'
    STATUS_REJECTED = 'rejected'
    STATUS_APPROVED = 'approved'
    STATUS_REVIEW = 'review'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = Choices(
        (STATUS_DRAFT, _('Draft')),
        (STATUS_SUBMISSION_REVIEW, _('Submission Review')),
        (STATUS_SUBMITTED, _('Submitted')),
        (STATUS_REJECTED, _('Rejected')),
        (STATUS_APPROVED, _('Approved')),
        (STATUS_REVIEW, _('Review')),
        (STATUS_COMPLETED, _('Completed')),
        (STATUS_CANCELLED, _('Cancelled')),
    )

    AUTO_TRANSITIONS = {}
    TRANSITION_SIDE_EFFECTS = {
        STATUS_SUBMISSION_REVIEW: [trip_subreview],
        STATUS_SUBMITTED: [trip_submitted],
        STATUS_REJECTED: [trip_rejected],
        STATUS_APPROVED: [trip_approved],
    }

    reference_number = models.CharField(
        max_length=100,
        verbose_name=_("Reference Number"),
        unique=True,
    )
    status = FSMField(
        verbose_name=_('Status'),
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )
    not_as_planned = models.BooleanField(
        verbose_name=_('Trip completed not as planned'),
        default=False)

    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('Supervisor'),
        on_delete=models.CASCADE,
        related_name="supervised_itineraries",
    )
    title = models.CharField(
        max_length=120,
        verbose_name=_("Title"),
        blank=True,
    )
    description = models.TextField(
        verbose_name=_("Description"),
        blank=True,
    )
    start_date = models.DateField(
        verbose_name=_('Start Date'),
        null=True,
        blank=True,
    )
    end_date = models.DateField(
        verbose_name=_('End Date'),
        null=True,
        blank=True,
    )
    traveller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Traveller"),
        on_delete=models.CASCADE,
        related_name="itineraries",
    )
    attachments = CodedGenericRelation(
        Attachment,
        verbose_name=_('Attachments'),
        code='travel_docs',
        blank=True,
    )
    additional_notes = models.TextField(
        verbose_name=_("Description"),
        blank=True,
        null=True
    )
    office = models.ForeignKey(
        Office,
        verbose_name=_("Office"),
        on_delete=models.DO_NOTHING,
        related_name="trips",
    )
    section = models.ForeignKey(
        Section,
        verbose_name=_("Section"),
        on_delete=models.DO_NOTHING,
        related_name="trips",
    )
    # stores information about the visit that will be displayed to the user,
    # the keys are interpretable error codes, that can be generated based on specific logic.
    user_info_text = models.JSONField(verbose_name="User Information Text", default=dict, blank=True)

    class Meta:
        verbose_name = _('Trip')
        verbose_name_plural = _('Trips')
        ordering = ("-start_date",)

    @classmethod
    def permission_structure(cls):
        permissions = import_permissions(cls.__name__)
        return permissions

    def __str__(self):
        return f'{self.traveller} [{self.get_status_display()}] {self.reference_number}'

    def get_reference_number(self):
        return "{code}/{year}TRAVEL{num}".format(
            code=connection.tenant.country_short_code,
            year=timezone.now().year,
            num=self.pk,
        )

    def dismiss_infotext(self, code):
        self.user_info_text.pop(code)

    def update_ma_deleted_infotext(self, ma):
        # code is composed TYPE|ACTION|IDs[..]
        code = f"MA|X|{ma.id}"
        self.user_info_text[code] = "A monitoring activity previously selected has been deleted from the" \
            " Field Monitoring Module, please review your Travel Activities"

    def update_ma_traveler_excluded_infotext(self, ma, act):
        code = f"MA|E|{ma.id}|{act.id}"
        self.user_info_text[code] = f"The monitoring activity {ma.number} has been updated to exclude the current" \
            f" trip traveller, please verify and update your Travel Activities accordingly"

    def update_ma_dates_changed_infotext(self, ma, act):
        code = f"MA|D|{ma.id}|{act.id}"
        self.user_info_text[code] = f"The monitoring activity {ma.number} has been updated and dates have changed" \
            f" please verify and update your Travel Activities and Itinerary accordingly"

    def get_object_url(self, **kwargs):
        return build_frontend_url(
            'travel',
            'trip',
            'detail',
            self.pk,
            **kwargs,
        )

    def get_rejected_comment(self):
        rejected_qs = self.status_history.filter(
            status=Trip.STATUS_REJECTED,
        )
        if rejected_qs.exists():
            return rejected_qs.first().comment
        return None

    def get_cancelled_comment(self):
        cancel_qs = self.status_history.filter(
            status=Trip.STATUS_CANCELLED,
        )
        if cancel_qs.exists():
            return cancel_qs.first().comment
        return None

    def get_completed_comment(self):
        completed_qs = self.status_history.filter(
            status=Trip.STATUS_COMPLETED,
        )
        if completed_qs.exists():
            return completed_qs.first().comment
        return None

    def get_mail_context(self, user):
        context = {
            "url": self.get_object_url(user=user),
            "trip": self
        }
        if self.status == self.STATUS_REJECTED:
            context["rejected_comment"] = self.get_rejected_comment()
        return context

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.reference_number:
            self.reference_number = self.get_reference_number()
            self.save()
        try:
            self.report
        except Report.DoesNotExist:
            Report.objects.create(trip=self)

    @transition(
        field=status,
        source=[STATUS_DRAFT],
        target=[STATUS_SUBMISSION_REVIEW],
    )
    def transition_to_submission_review(self):
        """Trip moves to submission review status"""

    @transition(
        field=status,
        source=[STATUS_DRAFT, STATUS_SUBMISSION_REVIEW],
        target=[STATUS_SUBMITTED],
    )
    def transition_to_submitted(self):
        """Trip moves to submitted status"""

    @transition(
        field=status,
        source=[STATUS_DRAFT, STATUS_SUBMITTED, STATUS_SUBMISSION_REVIEW],
        target=[STATUS_APPROVED],
    )
    def transition_to_approved(self):
        """Trip moves to approved status"""

    @transition(
        field=status,
        source=[STATUS_APPROVED],
        target=[STATUS_REVIEW],
    )
    def transition_to_review(self):
        """Trip moves to review status"""

    @transition(
        field=status,
        source=[STATUS_APPROVED, STATUS_REVIEW],
        target=[STATUS_COMPLETED],
    )
    def transition_to_completed(self):
        """Trip moves to completed status"""

    @transition(
        field=status,
        source=[
            STATUS_DRAFT,
            STATUS_SUBMISSION_REVIEW,
            STATUS_REJECTED,
            STATUS_APPROVED,
        ],
        target=[STATUS_CANCELLED],
    )
    def transition_to_cancelled(self):
        """Trip moves to cancelled status"""

    @transition(
        field=status,
        source=[STATUS_REJECTED, STATUS_SUBMISSION_REVIEW],
        target=[STATUS_DRAFT],
    )
    def transition_to_draft(self):
        """Trip moves to draft status"""

    # illegal transitions
    @transition(
        field=status,
        source=[
            STATUS_SUBMISSION_REVIEW,
            STATUS_SUBMITTED,
            STATUS_APPROVED,
            STATUS_REVIEW,
            STATUS_COMPLETED,
            STATUS_CANCELLED,
        ],
        target=[STATUS_DRAFT],
        conditions=[trip_illegal_transition],
    )
    def transition_to_draft_invalid(self):
        """Not allowed to move to draft status"""

    @transition(
        field=status,
        source=[
            STATUS_SUBMITTED,
            STATUS_APPROVED,
            STATUS_REVIEW,
            STATUS_COMPLETED,
            STATUS_REJECTED,
            STATUS_CANCELLED,
        ],
        target=[STATUS_SUBMISSION_REVIEW],
        conditions=[trip_illegal_transition],
    )
    def transition_to_submission_review_invalid(self):
        """Not allowed to move to submission review status"""

    @transition(
        field=status,
        source=[
            STATUS_APPROVED,
            STATUS_REVIEW,
            STATUS_COMPLETED,
            STATUS_REJECTED,
            STATUS_CANCELLED,
        ],
        target=[STATUS_SUBMITTED],
        conditions=[trip_illegal_transition],
    )
    def transition_to_submitted_invalid(self):
        """Not allowed to move to submitted status"""

    @transition(
        field=status,
        source=[
            STATUS_SUBMISSION_REVIEW,
            STATUS_REVIEW,
            STATUS_COMPLETED,
            STATUS_REJECTED,
            STATUS_CANCELLED,
        ],
        target=[STATUS_APPROVED],
        conditions=[trip_illegal_transition],
    )
    def transition_to_approved_invalid(self):
        """Not allowed to move to approved status"""

    @transition(
        field=status,
        source=[
            STATUS_DRAFT,
            STATUS_SUBMISSION_REVIEW,
            STATUS_SUBMITTED,
            STATUS_COMPLETED,
            STATUS_REJECTED,
            STATUS_CANCELLED,
        ],
        target=[STATUS_REVIEW],
        conditions=[trip_illegal_transition],
    )
    def transition_to_review_invalid(self):
        """Not allowed to move to review status"""

    @transition(
        field=status,
        source=[
            STATUS_DRAFT,
            STATUS_SUBMISSION_REVIEW,
            STATUS_SUBMITTED,
            STATUS_APPROVED,
            STATUS_REJECTED,
            STATUS_CANCELLED,
        ],
        target=[STATUS_COMPLETED],
        conditions=[trip_illegal_transition],
    )
    def transition_to_completed_invalid(self):
        """Not allowed to move to completed status"""

    @transition(
        field=status,
        source=[
            STATUS_DRAFT,
            STATUS_SUBMISSION_REVIEW,
            STATUS_APPROVED,
            STATUS_REVIEW,
            STATUS_COMPLETED,
            STATUS_CANCELLED,
        ],
        target=[STATUS_REJECTED],
        conditions=[trip_illegal_transition],
    )
    def transition_to_rejected_invalid(self):
        """Not allowed to move to rejected status"""

    @transition(
        field=status,
        source=[
            STATUS_SUBMITTED,
            STATUS_REVIEW,
            STATUS_COMPLETED,
        ],
        target=[STATUS_CANCELLED],
        conditions=[trip_illegal_transition],
    )
    def transition_to_cancelled_invalid(self):
        """Allowed to move to cancelled status"""


class ItineraryItem(TimeStampedModel):
    METHOD_BUS = 'bus'
    METHOD_CAR = 'car'
    METHOD_CHOICES = Choices(
        (METHOD_BUS, _('Bus')),
        (METHOD_CAR, _('Car'))
    )

    trip = models.ForeignKey(
        Trip,
        verbose_name=_("Trip"),
        on_delete=models.CASCADE,
        related_name="itinerary_items",
    )
    start_date = models.DateField(
        verbose_name=_('Start Date'),
        null=True,
        blank=True,
    )
    end_date = models.DateField(
        verbose_name=_('End Date'),
        null=True,
        blank=True,
    )
    travel_method = models.CharField(
        max_length=150,
        verbose_name=_("Travel Method"),
        blank=True
    )
    destination = models.CharField(
        max_length=150,
        verbose_name=_("Destination"),
        blank=True,
    )
    monitoring_activity = models.ForeignKey(
        MonitoringActivity,
        on_delete=models.CASCADE,
        related_name='trip_itinerary_items',
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = "Itinerary Item"
        verbose_name_plural = "Itinerary Items"

    def update_values_from_ma(self, ma=None):
        if not ma:
            if not self.monitoring_activity:
                raise Exception("trying to update values for an item without a monitoring activity")
            ma = self.monitoring_activity

        self.destination = ma.destination_str
        self.start_date = ma.start_date
        self.end_date = ma.end_date

    def __str__(self):
        return f"{self.trip} Item {self.start_date} - {self.end_date}"


class TripStatusHistory(TimeStampedModel):
    trip = models.ForeignKey(
        Trip,
        verbose_name=_("Trip"),
        on_delete=models.CASCADE,
        related_name="status_history",
    )
    status = models.CharField(
        max_length=30,
        choices=Trip.STATUS_CHOICES,
    )
    comment = models.TextField(blank=True)

    class Meta:
        verbose_name = _("Trip Status History")
        verbose_name_plural = _("Trip Status History")
        ordering = ("-created",)

    def __str__(self):
        return f"{self.get_status_display()} [{self.created}]"


class Activity(TimeStampedModel):
    TYPE_PROGRAMME_MONITORING = 'Monitoring Activity'
    TYPE_TECHNICAL_SUPPORT = 'Technical Support'
    TYPE_MEETING = 'Meeting'
    TYPE_STAFF_DEVELOPMENT = 'Staff Development'
    TYPE_STAFF_ENTITLEMENT = 'Staff Entitlement'
    TYPE_CHOICES = (
        (TYPE_PROGRAMME_MONITORING, 'Monitoring Activity'),
        (TYPE_TECHNICAL_SUPPORT, 'Technical Support'),
        (TYPE_MEETING, 'Meeting'),
        (TYPE_STAFF_DEVELOPMENT, 'Staff Development'),
        (TYPE_STAFF_ENTITLEMENT, 'Staff Entitlement'),
    )

    trip = models.ForeignKey(
        Trip,
        verbose_name=_("Trip"),
        on_delete=models.CASCADE,
        related_name="activities",
    )
    activity_date = models.DateField(
        verbose_name=_("Activity Date")
    )
    activity_type = models.CharField(
        max_length=64,
        verbose_name=_("Activity Type"),
        choices=TYPE_CHOICES,
        default=TYPE_PROGRAMME_MONITORING,
        blank=True,
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.DO_NOTHING,
        related_name="trip_activities",
        null=True,
        blank=True
    )
    monitoring_activity = models.ForeignKey(
        MonitoringActivity,
        on_delete=models.CASCADE,
        related_name="trip_activities",
        null=True,
        blank=True
    )
    partner = models.ForeignKey(
        PartnerOrganization,
        on_delete=models.CASCADE,
        related_name="trip_activities",
        null=True,
        blank=True
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        related_name="trip_activities",
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = _("Activity")
        verbose_name_plural = _("Activities")
        ordering = ["-activity_date"]

    def __str__(self):
        return f"{self.get_activity_type_display()} - {self.activity_date}"

    @transaction.atomic
    def save(self, **kwargs):
        super().save(**kwargs)
        if self.monitoring_activity:
            ma = self.monitoring_activity
            ItineraryItem.objects.update_or_create(
                trip=self.trip,
                monitoring_activity=ma,
                defaults={
                    "destination": ma.destination_str,
                    "start_date": ma.start_date,
                    "end_date": ma.end_date,
                    "monitoring_activity": ma
                }
            )

    @transaction.atomic
    def delete(self):
        if self.monitoring_activity:
            ma = self.monitoring_activity
            ItineraryItem.objects.filter(trip=self.trip, monitoring_activity=ma).delete()
        super().delete()


class Report(TimeStampedModel):
    trip = models.OneToOneField(
        Trip,
        verbose_name=_("Trip"),
        on_delete=models.CASCADE,
        related_name="report",
    )
    narrative = models.TextField(
        verbose_name=_("Narrative"),
        blank=True,
    )
    attachments = CodedGenericRelation(
        Attachment,
        verbose_name=_('Attachments'),
        code='travel_report_docs',
        blank=True,
    )

    class Meta:
        verbose_name = _("Report")
        verbose_name_plural = _("Reports")

    def __str__(self):
        return f"{self.trip} Report"
