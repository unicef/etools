from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import connection, models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from django_fsm import FSMField, transition
from model_utils import Choices
from model_utils.models import TimeStampedModel
from unicef_attachments.models import Attachment
from unicef_djangolib.fields import CodedGenericRelation
from unicef_locations.models import Location

from etools.applications.action_points.models import ActionPoint
from etools.applications.core.permissions import import_permissions
from etools.applications.core.urlresolvers import build_frontend_url
from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.partners.models import PartnerOrganization
from etools.applications.reports.models import Section
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
    # office =
    # section =

    class Meta:
        verbose_name = _('Trip')
        verbose_name_plural = _('Itineraries')
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

    @transition(
        field=status,
        source=[STATUS_DRAFT],
        target=[STATUS_SUBMISSION_REVIEW],
    )
    def transition_to_submission_review(self):
        """Trip moves to submission review status"""

    @transition(
        field=status,
        source=[STATUS_SUBMISSION_REVIEW],
        target=[STATUS_SUBMITTED],
    )
    def transition_to_submitted(self):
        """Trip moves to submitted status"""

    @transition(
        field=status,
        source=[STATUS_SUBMITTED, STATUS_SUBMISSION_REVIEW],
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
            STATUS_DRAFT,
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
            STATUS_DRAFT,
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

    class Meta:
        verbose_name = "Itinerary Item"
        verbose_name_plural = "Itinerary Items"

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
        on_delete=models.CASCADE,
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
    # location

    class Meta:
        verbose_name = _("Activity")
        verbose_name_plural = _("Activities")
        ordering = ["-activity_date"]

    def __str__(self):
        return f"{self.get_activity_type_display()} - {self.activity_date}"


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
