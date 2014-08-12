__author__ = 'jcranwellward'

import datetime

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import (
    GenericForeignKey, GenericRelation
)
from django.db.models.signals import post_save, post_delete
from django.contrib.sites.models import Site

from filer.fields.file import FilerFileField
from post_office import mail
from post_office.models import EmailTemplate
import reversion
from raven import Client

from EquiTrack.utils import AdminURLMixin
from locations.models import LinkedLocation
from reports.models import WBS
from funds.models import Grant

User = get_user_model()

User.__unicode__ = lambda user: user.get_full_name()

BOOL_CHOICES = (
    (None, "N/A"),
    (True, "Yes"),
    (False, "No")
)


def notify_on_delete(sender, instance, using, **kwargs):
    client = Client()
    client.captureMessage('An instance of {} was deleted: {}'.format(
        sender, instance
    ))

post_delete.connect(notify_on_delete)


def send_mail(sender, template, variables, *recipients):
    mail.send(
        [recp for recp in recipients],
        sender,
        template=template,
        context=variables,
    )


class Office(models.Model):
    name = models.CharField(max_length=254)

    def __unicode__(self):
        return self.name


class Trip(AdminURLMixin, models.Model):

    PLANNED = u'planned'
    APPROVED = u'approved'
    COMPLETED = u'completed'
    CANCELLED = u'cancelled'
    TRIP_STATUS = (
        (PLANNED, u"Planned"),
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
        if self.status == Trip.PLANNED and self.can_be_approved:
            self.approved_date = datetime.datetime.today()
            self.status = Trip.APPROVED
        super(Trip, self).save(**kwargs)

    @classmethod
    def send_trip_request(cls, sender, instance, created, **kwargs):
        current_site = Site.objects.get_current()
        state = 'Created' if created else 'Updated'

        recipients = [
            instance.owner.email,
            instance.supervisor.email]
        if instance.budget_owner:
            recipients.append(instance.budget_owner.email)
        send_mail(
            instance.owner.email,
            'trips/trip/created/updated',
            {
                'owner_name': instance.owner.get_full_name(),
                'number': instance.reference(),
                'state': state,
                'url': 'http://{}{}'.format(
                    current_site.domain,
                    instance.get_admin_url()
                )
            },
            *recipients
        )

        if instance.status == Trip.CANCELLED:
            email_name = 'trips/trip/cancelled'
            try:
                template = EmailTemplate.objects.get(
                    name=email_name
                )
            except EmailTemplate.DoesNotExist:
                template = EmailTemplate.objects.create(
                    name=email_name,
                    description='The email that is sent to everyone if a trip has been cancelled',
                    subject="Trip Cancelled: {{trip_reference}}",
                    content="The following trip has been cancelled: {{trip_reference}}"
                            "\r\n\r\n{{url}}"
                            "\r\n\r\nThank you."
                )

            if instance.travel_assistant:
                recipients.append(instance.travel_assistant.email)
            send_mail(
                instance.owner.email,
                template,
                {
                    'trip_reference': instance.reference(),
                    'url': 'http://{}{}'.format(
                        current_site.domain,
                        instance.get_admin_url()
                    )
                },
                *recipients
            )

        if instance.status == Trip.APPROVED:
            email_name = 'trips/trip/approved'
            try:
                template = EmailTemplate.objects.get(
                    name=email_name
                )
            except EmailTemplate.DoesNotExist:
                template = EmailTemplate.objects.create(
                    name=email_name,
                    description='The email that is sent to the traveller if a trip has been approved',
                    subject="Trip Approved: {{trip_reference}}",
                    content="The following trip has been approved: {{trip_reference}}"
                            "\r\n\r\n{{url}}"
                            "\r\n\r\nThank you."
                )
            send_mail(
                instance.owner.email,
                template,
                {
                    'trip_reference': instance.reference(),
                    'url': 'http://{}{}'.format(
                        current_site.domain,
                        instance.get_admin_url()
                    )
                },
                *recipients
            )
            if instance.travel_assistant and not instance.transport_booked:
                email_name = "travel/trip/travel_or_admin_assistant"
                try:
                    template = EmailTemplate.objects.get(
                        name=email_name
                    )
                except EmailTemplate.DoesNotExist:
                    template = EmailTemplate.objects.create(
                        name=email_name,
                        description="This e-mail will be sent when the trip is approved by the supervisor. "
                                    "It will go to the travel assistant to prompt them to organise the travel "
                                    "(vehicles, flights etc.) and request security clearance.",
                        subject="Travel for {{owner_name}}",
                        content="Dear {{travel_assistant}},"
                                "\r\n\r\nPlease organise the travel and security clearance (if needed) for the following trip:"
                                "\r\n\r\n{{url}}"
                                "\r\n\r\nThanks,"
                                "\r\n{{owner_name}}"
                    )
                send_mail(
                    instance.owner.email,
                    template,
                    {
                        'owner_name': instance.owner.get_full_name(),
                        'travel_assistant': instance.travel_assistant.get_full_name(),
                        'url': 'http://{}{}'.format(
                            current_site.domain,
                            instance.get_admin_url()
                        )
                    },
                    instance.travel_assistant.email,
                )

            if instance.ta_required and instance.programme_assistant and not instance.ta_drafted:
                email_name = 'trips/trip/TA_request'
                try:
                    template = EmailTemplate.objects.get(
                        name=email_name
                    )
                except EmailTemplate.DoesNotExist:
                    template = EmailTemplate.objects.create(
                        name=email_name,
                        description="This email is sent to the relevant programme assistant to create "
                                    "the TA for the staff in concern after the approval of the supervisor.",
                        subject="Travel Authorization request for {{owner_name}}",
                        content="Dear {{pa_assistant}},"
                                "\r\n\r\nKindly draft my Travel Authorization in Vision based on the approved trip:"
                                "\r\n\r\n{{url}}"
                                "\r\n\r\nThanks,"
                                "\r\n{{owner_name}}"
                    )
                send_mail(
                    instance.owner.email,
                    template,
                    {
                        'owner_name': instance.owner.get_full_name(),
                        'pa_assistant': instance.programme_assistant.get_full_name(),
                        'url': 'http://{}{}'.format(
                            current_site.domain,
                            instance.get_admin_url()
                        )
                    },
                    instance.programme_assistant.email,
                )

            if instance.ta_drafted and instance.vision_approver:
                email_name = 'trips/trip/TA_drafted'
                try:
                    template = EmailTemplate.objects.get(
                        name=email_name
                    )
                except EmailTemplate.DoesNotExist:
                    template = EmailTemplate.objects.create(
                        name=email_name,
                        description="This email is sent to the relevant colleague to approve "
                                    "the TA for the staff in concern after the TA has been drafted in VISION.",
                        subject="Travel Authorization drafted for {{owner_name}}",
                        content="Dear {{vision_approver}},"
                                "\r\n\r\nKindly approve my Travel Authorization ({{ta_ref}}) in VISION based on the approved trip:"
                                "\r\n\r\n{{url}}"
                                "\r\n\r\nThanks,"
                                "\r\n{{owner_name}}"
                    )
                send_mail(
                    instance.owner.email,
                    template,
                    {
                        'owner_name': instance.owner.get_full_name(),
                        'vision_approver': instance.vision_approver.get_full_name(),
                        'ta_ref': instance.ta_reference,
                        'url': 'http://{}{}'.format(
                            current_site.domain,
                            instance.get_admin_url()
                        )
                    },
                    instance.vision_approver.email,
                )


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
    persons_responsible = models.ManyToManyField(User)
    actions_taken = models.TextField(blank=True, null=True)
    completed_date = models.DateField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True, verbose_name='Supervisors Comments')
    closed = models.BooleanField(default=False)

    @classmethod
    def send_action(cls, sender, instance, created, **kwargs):
        current_site = Site.objects.get_current()
        if created:
            email_name = 'trips/action/created'
            try:
                template = EmailTemplate.objects.get(
                    name=email_name
                )
            except EmailTemplate.DoesNotExist:
                template = EmailTemplate.objects.create(
                    name=email_name,
                    description='Sent when trip action points are created',
                    subject='Trip action point created for trip: {{trip_reference}}',
                    content="A new trip action point has been created "
                            "and awaits your action here:"
                            "\r\n\r\n{{url}}"
                            "\r\n\r\nThank you."
                )
            send_mail(
                instance.trip.owner.email,
                template,
                {
                    'trip_reference': instance.trip.reference(),
                    'url': 'http://{}{}#reporting'.format(
                        current_site.domain,
                        instance.trip.get_admin_url()
                    )
                },
                *[instance.trip.budget_owner.email, instance.trip.supervisor.email] +
                [user.email for user in instance.persons_responsible.all()]
            )
        if instance.closed:
            email_name = 'trips/action/closed'
            try:
                template = EmailTemplate.objects.get(
                    name=email_name
                )
            except EmailTemplate.DoesNotExist:
                template = EmailTemplate.objects.create(
                    name=email_name,
                    description='Sent when trip action points are closed',
                    subject='Trip action point closed for trip: {{trip_reference}}',
                    content="A trip action point has been closed here:"
                            "\r\n\r\n{{url}}"
                            "\r\n\r\nThank you."
                )
            send_mail(
                instance.trip.owner.email,
                template,
                {
                    'trip_reference': instance.trip.reference(),
                    'url': 'http://{}{}#reporting'.format(
                        current_site.domain,
                        instance.trip.get_admin_url()
                    )
                },
                *[instance.trip.budget_owner.email, instance.trip.supervisor.email] +
                [user.email for user in instance.persons_responsible.all()]
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
