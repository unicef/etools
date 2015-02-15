__author__ = 'jcranwellward'

import datetime

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import (
    GenericForeignKey, GenericRelation
)
from django.db.models.signals import post_save
from django.contrib.sites.models import Site

from filer.fields.file import FilerFileField
import reversion

from EquiTrack.mixins import AdminURLMixin
from locations.models import LinkedLocation
from reports.models import WBS
from funds.models import Grant
from . import emails

User = get_user_model()

User.__unicode__ = lambda user: user.get_full_name()
User._meta.ordering = ['first_name']

BOOL_CHOICES = (
    (None, "N/A"),
    (True, "Yes"),
    (False, "No")
)


class Office(models.Model):
    name = models.CharField(max_length=254)

    def __unicode__(self):
        return self.name


class Trip(AdminURLMixin, models.Model):

    PLANNED = u'planned'
    SUBMITTED = u'submitted'
    APPROVED = u'approved'
    COMPLETED = u'completed'
    CANCELLED = u'cancelled'
    TRIP_STATUS = (
        (PLANNED, u"Planned"),
        (SUBMITTED, u"Submitted"),
        (APPROVED, u"Approved"),
        (COMPLETED, u"Completed"),
        (CANCELLED, u"Cancelled"),
    )

    DUTY_TRAVEL = u'duty_travel'
    HOME_LEAVE = u'home_leave'
    FAMILY_VISIT = u'family_visit'
    EDUCATION_GRANT = u'education_grant'
    STAFF_DEVELOPMENT = u'staff_development'
    TRAVEL_TYPE = (
        (DUTY_TRAVEL, u"DUTY TRAVEL"),
        (HOME_LEAVE, u"HOME LEAVE"),
        (FAMILY_VISIT, u"FAMILY VISIT"),
        (EDUCATION_GRANT, u"EDUCATION GRANT"),
        (STAFF_DEVELOPMENT, u"STAFF DEVELOPMENT"),
    )

    status = models.CharField(
        max_length=32L,
        choices=TRIP_STATUS,
        default=PLANNED,
    )
    cancelled_reason = models.CharField(
        max_length=254,
        blank=True, null=True,
        help_text='Please provide a reason if the mission is cancelled'
    )
    purpose_of_travel = models.CharField(
        max_length=254
    )
    travel_type = models.CharField(
        max_length=32L,
        choices=TRAVEL_TYPE,
        default=DUTY_TRAVEL
    )
    international_travel = models.BooleanField(
        default=False,
        help_text='International travel will require approval from the representative'
    )
    from_date = models.DateField()
    to_date = models.DateField()
    monitoring_supply_delivery = models.BooleanField(default=False)
    no_pca = models.BooleanField(
        default=False,
        verbose_name=u'Not related to a PCA',
        help_text='Tick this if this trip is not related to partner monitoring'
    )
    pcas = models.ManyToManyField(
        u'partners.PCA',
        blank=True, null=True,
        verbose_name=u"Related PCAs"
    )
    partners = models.ManyToManyField(
        u'partners.PartnerOrganization',
        blank=True, null=True
    )
    main_observations = models.TextField(
        blank=True, null=True
    )

    ta_required = models.BooleanField(
        default=False,
        help_text='Is a Travel Authorisation (TA) is required?'
    )
    programme_assistant = models.ForeignKey(
        User,
        blank=True, null=True,
        verbose_name='Staff Responsible for TA',
        help_text='Needed if a Travel Authorisation (TA) is required',
        related_name='managed_trips'
    )

    ta_drafted = models.BooleanField(
        default=False,
        help_text='Has the TA been drafted in vision if applicable?'
    )
    ta_drafted_date = models.DateField(blank=True, null=True)
    ta_reference = models.CharField(max_length=254, blank=True, null=True)
    vision_approver = models.ForeignKey(
        User,
        blank=True, null=True,
        verbose_name='VISION Approver'
    )

    locations = GenericRelation(LinkedLocation)

    owner = models.ForeignKey(User, verbose_name='Traveller', related_name='trips')
    section = models.ForeignKey('reports.Sector', blank=True, null=True)
    office = models.ForeignKey(Office, blank=True, null=True)
    travel_assistant = models.ForeignKey(
        User,
        blank=True, null=True,
        related_name='organised_trips',
        verbose_name='Travel focal point'
    )
    transport_booked = models.BooleanField(default=False)
    security_granted = models.BooleanField(default=False)

    supervisor = models.ForeignKey(User, related_name='supervised_trips')
    approved_by_supervisor = models.BooleanField(default=False)
    date_supervisor_approved = models.DateField(blank=True, null=True)

    budget_owner = models.ForeignKey(User, related_name='budgeted_trips', blank=True, null=True,)
    approved_by_budget_owner = models.BooleanField(default=False)
    date_budget_owner_approved = models.DateField(blank=True, null=True)

    human_resources = models.ForeignKey(User, related_name='certified_trips', blank=True, null=True)
    approved_by_human_resources = models.NullBooleanField(
        default=None,
        choices=BOOL_CHOICES,
        verbose_name='Certified by human resources')
    date_human_resources_approved = models.DateField(blank=True, null=True)

    representative = models.ForeignKey(User, related_name='approved_trips', blank=True, null=True)
    representative_approval = models.NullBooleanField(default=None, choices=BOOL_CHOICES)
    date_representative_approved = models.DateField(blank=True, null=True)

    approved_date = models.DateField(blank=True, null=True)
    created_date = models.DateTimeField(auto_now_add=True)
    approved_email_sent = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_date']

    def __unicode__(self):
        return u'{}   {} - {}: {}'.format(
            self.reference(),
            self.from_date,
            self.to_date,
            self.purpose_of_travel
        )

    def reference(self):
        return '{}/{}-{}'.format(
            self.created_date.year,
            self.id,
            self.trip_revision
        ) if self.id else None
    reference.short_description = 'Reference'

    def outstanding_actions(self):
        return self.actionpoint_set.filter(
            closed=False).count()

    @property
    def trip_revision(self):
        return reversion.get_for_object(self).count()

    @property
    def requires_hr_approval(self):
        return self.travel_type in [
            Trip.HOME_LEAVE,
            Trip.FAMILY_VISIT,
            Trip.EDUCATION_GRANT,
            Trip.STAFF_DEVELOPMENT]

    @property
    def requires_rep_approval(self):
        return self.international_travel

    @property
    def can_be_approved(self):
        if not self.approved_by_supervisor:
            return False
        if self.requires_hr_approval\
        and not self.approved_by_human_resources:
            return False
        if self.requires_rep_approval\
        and not self.representative_approval:
            return False
        return True

    def save(self, **kwargs):
        if self.status == Trip.SUBMITTED and self.can_be_approved:
            self.approved_date = datetime.datetime.today()
            self.status = Trip.APPROVED
        super(Trip, self).save(**kwargs)

    @classmethod
    def send_trip_request(cls, sender, instance, created, **kwargs):
        """
        Trip emails alerts are sent at various stages...
        """
        # default list of recipients
        recipients = [
            instance.owner.email,
            instance.supervisor.email]
        if instance.budget_owner:
            recipients.append(instance.budget_owner.email)
        if instance.international_travel:
            recipients.append(instance.representative.email)

        if instance.status == Trip.SUBMITTED:
            emails.TripCreatedEmail(instance).send(
                instance.owner.email,
                *recipients
            )
        elif instance.status == Trip.CANCELLED:
            # send an email to everyone if the trip is cancelled
            emails.TripCancelledEmail(instance).send(
                instance.owner.email,
                *recipients
            )
        elif instance.status == Trip.APPROVED:

            if instance.travel_assistant and not instance.transport_booked:
                emails.TripTravelAssistantEmail(instance).send(
                    instance.owner.email,
                    instance.travel_assistant.email
                )

            if instance.ta_required and instance.programme_assistant and not instance.ta_drafted:
                emails.TripTAEmail(instance).send(
                    instance.owner.email,
                    instance.programme_assistant.email
                )

            if instance.ta_drafted and instance.vision_approver:
                emails.TripTADraftedEmail(instance).send(
                    instance.programme_assistant.email,
                    instance.vision_approver.email
                )

            if not instance.approved_email_sent:
                emails.TripApprovedEmail(instance).send(
                    instance.owner.email,
                    *recipients
                )
                instance.approved_email_sent = True
                instance.save()


post_save.connect(Trip.send_trip_request, sender=Trip)


class TripFunds(models.Model):

    trip = models.ForeignKey(Trip)
    wbs = models.ForeignKey(WBS)
    grant = models.ForeignKey(Grant)
    amount = models.PositiveIntegerField(
        verbose_name='Percentage (%)'
    )

    class Meta:
        verbose_name = u'Funding'
        verbose_name_plural = u'Funding'


class TravelRoutes(models.Model):

    trip = models.ForeignKey(Trip)
    origin = models.CharField(max_length=254)
    destination = models.CharField(max_length=254)
    depart = models.DateTimeField()
    arrive = models.DateTimeField()
    remarks = models.CharField(max_length=254, null=True, blank=True)

    class Meta:
        verbose_name = u'Travel Itinerary'
        verbose_name_plural = u'Travel Itinerary'


class ActionPoint(models.Model):

    trip = models.ForeignKey(Trip)
    description = models.CharField(max_length=254)
    due_date = models.DateField()
    person_responsible = models.ForeignKey(User, related_name='for_action')
    persons_responsible = models.ManyToManyField(User)
    actions_taken = models.TextField(blank=True, null=True)
    completed_date = models.DateField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    closed = models.BooleanField(default=False)

    def __unicode__(self):
        return self.description

    @classmethod
    def send_action(cls, sender, instance, created, **kwargs):

        recipients = [
            user.email
            for user in
            instance.persons_responsible.all()
        ]
        recipients.append(instance.trip.supervisor.email)

        if created:
            emails.TripActionPointCreated(instance).send(
                instance.trip.owner.email,
                *recipients
            )
        elif instance.closed:
            emails.TripActionPointClosed(instance).send(
                instance.trip.owner.email,
                *recipients
            )
        else:
            emails.TripActionPointUpdated(instance).send(
                instance.trip.owner.email,
                *recipients
            )


post_save.connect(ActionPoint.send_action, sender=ActionPoint)


class FileAttachment(models.Model):

    type = models.ForeignKey(u'partners.FileType')
    file = FilerFileField()

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    def __unicode__(self):
        return self.file.name

    def download_url(self):
        if self.file:
            return u'<a class="btn btn-primary default" ' \
                   u'href="{}" >Download</a>'.format(self.file.file.url)
        return u''
    download_url.allow_tags = True
    download_url.short_description = 'Download Files'
