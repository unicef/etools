__author__ = 'jcranwellward'

import datetime
from copy import deepcopy

from django.db import models, connection, transaction
from django.db.models import Q
from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from django.db.models.signals import post_save
from django.contrib.sites.models import Site

from reversion.revisions import get_for_object
from smart_selects.db_fields import ChainedForeignKey

from EquiTrack.mixins import AdminURLMixin
from reports.models import Result, Sector
from funds.models import Grant
from users.models import Office, Section
from locations.models import Location
from partners.models import (
    PartnerOrganization,
    PCA,
    ResultChain,
    RAMIndicator,
    GovernmentIntervention,
    GovernmentInterventionResult
)
from . import emails

User = settings.AUTH_USER_MODEL

BOOL_CHOICES = (
    (None, "N/A"),
    (True, "Yes"),
    (False, "No")
)


class Trip(AdminURLMixin, models.Model):
    """
    Represents a trip for UNICEF staff

    Relates to :model:`partners.PCA`
    Relates to :model:`partners.PartnerOrganization`
    Relates to :model:`auth.User`
    Relates to :model:`users.Office`
    Relates to :model:`users.Section`
    """

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

    PROGRAMME_MONITORING = u'programme_monitoring'
    SPOT_CHECK = u'spot_check'
    ADVOCACY = u'advocacy'
    TECHNICAL_SUPPORT = u'technical_support'
    MEETING = u'meeting'
    DUTY_TRAVEL = u'duty_travel'
    HOME_LEAVE = u'home_leave'
    FAMILY_VISIT = u'family_visit'
    EDUCATION_GRANT = u'education_grant'
    STAFF_DEVELOPMENT = u'staff_development'
    STAFF_ENTITLEMENT = u'staff_entitlement'
    TRAVEL_TYPE = (
        (PROGRAMME_MONITORING, u'PROGRAMMATIC VISIT'),
        (SPOT_CHECK, u'SPOT CHECK'),
        (ADVOCACY, u'ADVOCACY'),
        (TECHNICAL_SUPPORT, u'TECHNICAL SUPPORT'),
        (MEETING, u'MEETING'),
        (STAFF_DEVELOPMENT, u"STAFF DEVELOPMENT"),
        (STAFF_ENTITLEMENT, u"STAFF ENTITLEMENT"),
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
        default=PROGRAMME_MONITORING
    )
    security_clearance_required = models.BooleanField(
        default=False,
        help_text='Do you need security clarance for this trip?'
    )
    international_travel = models.BooleanField(
        default=False,
        help_text='International travel will require approval from the representative'
    )
    from_date = models.DateField()
    to_date = models.DateField()

    pcas = models.ManyToManyField(
        u'partners.PCA',
        blank=True,
        verbose_name=u"Related Interventions"
    )
    partners = models.ManyToManyField(
        u'partners.PartnerOrganization',
        blank=True
    )
    main_observations = models.TextField(
        blank=True, null=True
    )
    constraints = models.TextField(
        blank=True, null=True
    )
    lessons_learned = models.TextField(
        blank=True, null=True
    )
    opportunities = models.TextField(
        blank=True, null=True
    )

    ta_required = models.BooleanField(
        default=False,
        verbose_name='TA required?',
        help_text='Is a Travel Authorisation (TA) is required?'
    )
    programme_assistant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True, null=True,
        verbose_name='Staff Responsible for TA',
        help_text='Needed if a Travel Authorisation (TA) is required',
        related_name='managed_trips'
    )

    ta_drafted = models.BooleanField(
        default=False,
        verbose_name='TA drafted?',
        help_text='Has the TA been drafted in vision if applicable?'
    )
    ta_drafted_date = models.DateField(
        blank=True, null=True,
        verbose_name='TA drafted date',
    )
    ta_reference = models.CharField(
        max_length=254,
        verbose_name='TA reference',
        blank=True, null=True
    )
    vision_approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True, null=True,
        verbose_name='VISION Approver'
    )

    driver = models.ForeignKey(User, related_name='trips_driver', verbose_name='Driver', null=True, blank=True)
    driver_supervisor = models.ForeignKey(User, verbose_name='Supervisor for Driver',
                                          related_name='driver_supervised_trips', null=True, blank=True)
    driver_trip = models.ForeignKey('self', null=True, blank=True, related_name='drivers_trip')

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='Traveller', related_name='trips')
    section = models.ForeignKey(Section, blank=True, null=True)
    office = models.ForeignKey(Office, blank=True, null=True)
    travel_assistant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True, null=True,
        related_name='organised_trips',
        verbose_name='Travel focal point'
    )
    transport_booked = models.BooleanField(default=False)
    security_granted = models.BooleanField(default=False)

    supervisor = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='supervised_trips')
    approved_by_supervisor = models.BooleanField(default=False)
    date_supervisor_approved = models.DateField(blank=True, null=True)

    budget_owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='budgeted_trips', blank=True, null=True,)
    approved_by_budget_owner = models.BooleanField(default=False)
    date_budget_owner_approved = models.DateField(blank=True, null=True)

    human_resources = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='certified_trips', blank=True, null=True)
    approved_by_human_resources = models.NullBooleanField(
        default=None,
        choices=BOOL_CHOICES,
        verbose_name='Certified by human resources',
        help_text='HR must approve all trips relating to training and staff development')
    date_human_resources_approved = models.DateField(blank=True, null=True)

    representative = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='approved_trips', blank=True, null=True)
    representative_approval = models.NullBooleanField(default=None, choices=BOOL_CHOICES)
    date_representative_approved = models.DateField(blank=True, null=True)

    approved_date = models.DateField(blank=True, null=True)
    created_date = models.DateTimeField(auto_now_add=True)
    approved_email_sent = models.BooleanField(default=False)
    submitted_email_sent = models.BooleanField(default=False)

    ta_trip_took_place_as_planned = models.BooleanField(
        default=False,
        verbose_name='TA trip took place as attached',
        help_text='I certify that the travel took place exactly as per the attached Travel Authorization and'
                  ' that there were no changes to the itinerary'
    )
    ta_trip_repay_travel_allowance = models.BooleanField(
        default=False,
        help_text='I certify that I will repay any travel allowance to which I am not entitled'
    )
    ta_trip_final_claim = models.BooleanField(
        default=False,
        help_text='I authorize UNICEF to treat this as the FINAL Claim'
    )
    pending_ta_amendment = models.BooleanField(
        default=False,
    )
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

    def attachments(self):
        return self.files.all().count()

    def outstanding_actions(self):
        return self.actionpoint_set.filter(
            status='open').count()

    @property
    def trip_revision(self):
        return get_for_object(self).count()

    @property
    def trip_overdue(self):
        if self.to_date < datetime.date.today() and self.status != Trip.COMPLETED:
            return True
        return False

    @property
    def requires_hr_approval(self):
        return self.travel_type in [
            # Trip.STAFF_DEVELOPMENT
        ]

    @property
    def requires_rep_approval(self):
        return self.international_travel

    @property
    def can_be_approved(self):
        if self.status != Trip.SUBMITTED:
            return False
        if not self.approved_by_supervisor:
            return False
        if self.requires_hr_approval \
                and not self.approved_by_human_resources:
            return False
        if self.requires_rep_approval \
                and not self.representative_approval:
            return False
        if self.ta_drafted \
                and not self.vision_approver:
            return False
        return True

    @transaction.atomic
    def save(self, **kwargs):
        # check if trip can be approved
        if self.can_be_approved:
            self.approved_date = datetime.date.today()
            self.status = Trip.APPROVED

        if self.status is not Trip.CANCELLED and self.cancelled_reason:
            self.status = Trip.CANCELLED

        if self.status == Trip.APPROVED and \
        self.driver is not None and \
        self.driver_supervisor is not None and \
        self.driver_trip is None:
            self.create_driver_trip()

        if self.status == Trip.COMPLETED and self.driver_trip:
            driver_trip = Trip.objects.get(id=self.driver_trip.id)
            driver_trip.status = Trip.COMPLETED
            driver_trip.save()

        # update partner hact values
        if self.status == Trip.COMPLETED and self.travel_type in [Trip.PROGRAMME_MONITORING, Trip.SPOT_CHECK]:
            if self.linkedgovernmentpartner_set:
                for gov_partner in self.linkedgovernmentpartner_set.all():
                    PartnerOrganization.programmatic_visits(gov_partner.partner, self)
                    PartnerOrganization.spot_checks(gov_partner.partner, self)

            if self.linkedpartner_set:
                for link_partner in self.linkedpartner_set.all():
                    PartnerOrganization.programmatic_visits(link_partner.partner, self)
                    PartnerOrganization.spot_checks(link_partner.partner, self)

        super(Trip, self).save(**kwargs)

    def create_driver_trip(self):
        trip = deepcopy(self)
        trip.pk = None
        trip.status = Trip.SUBMITTED
        trip.id = None
        trip.owner = self.driver
        trip.supervisor = self.driver_supervisor
        trip.approved_by_supervisor = False
        trip.date_supervisor_approved = None
        trip.approved_by_budget_owner = False
        trip.date_budget_owner_approved = None
        trip.approved_by_human_resources = None
        trip.representative_approval = None
        trip.date_representative_approved = None
        trip.approved_date = None
        trip.approved_email_sent = False
        trip.driver = None
        trip.driver_supervisor = None

        super(Trip, trip).save()

        for route in self.travelroutes_set.all():
            TravelRoutes.objects.create(
                trip=trip,
                origin=route.origin,
                destination=route.destination,
                depart=route.depart,
                arrive=route.arrive,
                remarks=route.remarks
            )

        for location in self.triplocation_set.all():
            TripLocation.objects.create(
                trip=trip,
                location=location.location
            )

        self.driver_trip = trip

    @property
    def all_files(self):
        return FileAttachment.objects.filter(object_id=self.id)

    @classmethod
    def get_current_trips(cls, user):
        super_trips = user.supervised_trips.filter(
            Q(status=Trip.APPROVED) | Q(status=Trip.SUBMITTED)
        )
        my_trips = user.trips.filter(
            Q(status=Trip.APPROVED) | Q(status=Trip.SUBMITTED) | Q(status=Trip.PLANNED)
        )
        return my_trips | super_trips

    @classmethod
    def send_trip_request(cls, sender, instance, created, **kwargs):
        """
        Trip emails alerts are sent at various stages...
        """
        # default list of recipients
        recipients = [
            instance.owner.email,
            instance.supervisor.email]

        #TODO: Make this work now that offices are moved into the global schema
        # get zonal chiefs emails if travelling in their respective zones
        # locations = instance.locations.all().values_list('governorate__id', flat=True)
        # offices = Office.objects.filter(location_id__in=locations)
        # zonal_chiefs = [office.zonal_chief.email for office in offices if office.zonal_chief]

        if instance.budget_owner:
            if instance.budget_owner.email not in recipients:
                recipients.append(instance.budget_owner.email)

        if instance.status == Trip.SUBMITTED:
            if instance.submitted_email_sent is False:
                emails.TripCreatedEmail(instance).send(
                    instance.owner.email,
                    *recipients
                )
                instance.submitted_email_sent = True
                instance.save()

            if instance.international_travel and instance.approved_by_supervisor:
                recipients.append(instance.representative.email)
                emails.TripRepresentativeEmail(instance).send(
                    instance.owner.email,
                    *recipients
                )

        elif instance.status == Trip.CANCELLED:
            # send an email to everyone if the trip is cancelled
            if instance.travel_assistant:
                recipients.append(instance.travel_assistant.email)

            #recipients.extend(zonal_chiefs)
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
                if instance.international_travel:
                    recipients.append(instance.representative.email)

                #recipients.extend(zonal_chiefs)
                emails.TripApprovedEmail(instance).send(
                    instance.owner.email,
                    *recipients
                )
                instance.approved_email_sent = True
                instance.save()

        elif instance.status == Trip.COMPLETED:
            emails.TripCompletedEmail(instance).send(
                instance.owner.email,
                *recipients
            )

post_save.connect(Trip.send_trip_request, sender=Trip)


class LinkedPartner(models.Model):
    """
    Represents a link between a partner, intervention and trip

    Relates to :model:`trips.Trip`
    Relates to :model:`partners.PartnerOrganization`
    Relates to :model:`partners.PCA`
    Relates to :model:`reports.ResultChain`
    """

    trip = models.ForeignKey(Trip)
    partner = models.ForeignKey(
        PartnerOrganization,
    )
    intervention = ChainedForeignKey(
        PCA,
        related_name='trips',
        chained_field="partner",
        chained_model_field="partner",
        show_all=False,
        auto_choose=True,
        blank=True, null=True,
    )
    result = ChainedForeignKey(
        ResultChain,
        chained_field="intervention",
        chained_model_field="partnership",
        show_all=False,
        auto_choose=True,
        blank=True, null=True,
    )


class LinkedGovernmentPartner(models.Model):
    """
    Represents a link between a partner, government intervention and trip

    Relates to :model:`trips.Trip`
    Relates to :model:`partners.PartnerOrganization`
    Relates to :model:`partners.GovernmentIntervention`
    Relates to :model:`partners.GovernmentInterventionResult`
    """

    trip = models.ForeignKey(Trip)
    partner = models.ForeignKey(
        PartnerOrganization,
    )
    intervention = ChainedForeignKey(
        GovernmentIntervention,
        related_name='trips',
        chained_field="partner",
        chained_model_field="partner",
        show_all=False,
        auto_choose=True,
        blank=True, null=True,
    )
    result = ChainedForeignKey(
        GovernmentInterventionResult,
        chained_field="intervention",
        chained_model_field="intervention",
        show_all=False,
        auto_choose=True,
        blank=True, null=True,
    )


class TripFunds(models.Model):
    """
    Represents funding used for the trip

    Relates to :model:`trips.Trip`
    Relates to :model:`results.Result`
    Relates to :model:`funds.Grant`
    """

    trip = models.ForeignKey(Trip)
    wbs = models.ForeignKey(
        Result, verbose_name='WBS'
    )
    grant = models.ForeignKey(Grant)
    amount = models.PositiveIntegerField(
        verbose_name='Percentage (%)'
    )

    class Meta:
        verbose_name = u'Funding'
        verbose_name_plural = u'Funding'


class TripLocation(models.Model):
    """
    Represents a location for the trip

    Relates to :model:`trips.Trip`
    Relates to :model:`loctions.Location`
    """

    trip = models.ForeignKey(Trip)
    location = models.ForeignKey(
        Location,
        null=True, blank=True
    )

    def __unicode__(self):
        desc = u'{} -> {} ({})'.format(
            self.location.parent.name if (self.location and self.location.parent) else u'',
            self.location.name if self.location else '',
            self.location.gateway.name if (self.location and self.location.gateway) else ''
        )

        return desc

    class Meta:
        ordering = ['id']


class TravelRoutes(models.Model):
    """
    Represents a travel route for the trip

    Relates to :model:`trips.Trip`
    """

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
    """
    Represents an action point for the trip

    Relates to :model:`trips.Trip`
    Relates to :model:`auth.User`
    """

    STATUS = (
        ('closed', 'Closed'),
        ('ongoing', 'On-going'),
        ('open', 'Open'),
        ('cancelled', 'Cancelled')
    )

    trip = models.ForeignKey(Trip)
    description = models.CharField(max_length=254)
    due_date = models.DateField()
    person_responsible = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='for_action')
    actions_taken = models.TextField(blank=True, null=True)
    completed_date = models.DateField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    status = models.CharField(choices=STATUS, max_length=254, null=True, verbose_name='Status')
    created_date = models.DateTimeField(auto_now_add=True)
    follow_up = models.BooleanField(default=False)

    def __unicode__(self):
        return self.description

    @property
    def overdue(self):
        return self.due_date <= datetime.date.today()

    @property
    def due_soon(self):
        delta = (self.due_date - datetime.date.today()).days
        return delta <= 2

    @property
    def traffic_color(self):
        if self.overdue:
            return 'red'
        elif self.due_soon:
            return 'yellow'
        else:
            return 'green'

    @classmethod
    def send_action(cls, sender, instance, created, **kwargs):

        recipients = [
            instance.trip.owner.email,
            instance.person_responsible.email,
            instance.trip.supervisor.email
        ]

        if created:
            emails.TripActionPointCreated(instance).send(
                instance.trip.owner.email,
                *recipients
            )
        elif instance.status == 'closed':
            emails.TripActionPointClosed(instance).send(
                instance.trip.owner.email,
                *recipients
            )
        else:
            emails.TripActionPointUpdated(instance).send(
                instance.trip.owner.email,
                *recipients
            )

    @transaction.atomic
    def save(self, **kwargs):
        # update hact values
        if self.completed_date is None and self.follow_up:
            if self.trip.linkedgovernmentpartner_set:
                for gov_partner in self.trip.linkedgovernmentpartner_set.all():
                    PartnerOrganization.follow_up_flags(gov_partner.partner, self)

            if self.trip.linkedpartner_set:
                for link_partner in self.trip.linkedpartner_set.all():
                    PartnerOrganization.follow_up_flags(link_partner.partner, self)
        return super(ActionPoint, self).save(**kwargs)

post_save.connect(ActionPoint.send_action, sender=ActionPoint)


def get_report_filename(instance, filename):
    return '/'.join([
        connection.schema_name,
        'trip_reports',
        str(instance.trip.id),
        filename
    ])


class FileAttachment(models.Model):
    """
    Represents a file attachment for the trip

    Relates to :model:`trips.Trip`
    Relates to :model:`partners.FileType`
    """

    trip = models.ForeignKey(Trip, null=True, blank=True, related_name=u'files')
    type = models.ForeignKey(u'partners.FileType')
    caption = models.TextField(
        null=True,
        blank=True,
        verbose_name='Caption / Description',
        help_text='Description of the file to upload: optional',
    )
    report = models.FileField(
        upload_to=get_report_filename,
        max_length=255,
    )

    content_type = models.ForeignKey(ContentType, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)

    def __unicode__(self):
        return u'{}: {}'.format(
            self.type.name,
            self.report.name
        )
