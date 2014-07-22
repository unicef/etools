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
from post_office import mail
from post_office.models import EmailTemplate

from EquiTrack.utils import AdminURLMixin
from locations.models import LinkedLocation
from reports.models import WBS
from funds.models import Grant

User = get_user_model()


def send_mail(sender, template, variables, *recipients):
    mail.send(
        [recp for recp in recipients],
        sender,
        template=template,
        context=variables,
    )


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
    activities_undertaken = models.CharField(
        max_length=254,
        verbose_name='Activities'
    )
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
        verbose_name='Assistant Responsible for TA',
        help_text='Needed if a Travel Authorisation (TA) is required',
        related_name='managed_trips'
    )
    wbs = models.ManyToManyField(
        WBS,
        blank=True, null=True,
        help_text='Needed if trip is over 10 hours and requires overnight stay'
    )
    grant = models.ManyToManyField(
        Grant,
        blank=True, null=True
    )
    ta_approved = models.BooleanField(
        default=False,
        help_text='Has the TA been approved in vision?'
    )
    ta_approved_date = models.DateField(blank=True, null=True)
    ta_reference = models.CharField(max_length=254, blank=True, null=True)

    locations = GenericRelation(LinkedLocation)

    owner = models.ForeignKey(User, verbose_name='Traveller')
    section = models.ForeignKey('reports.Sector', blank=True, null=True)

    travel_assistant = models.ForeignKey(
        User,
        blank=True, null=True,
        related_name='organised_trips'
    )
    transport_booked = models.BooleanField(default=False)
    security_clearance = models.BooleanField(default=False)
    supervisor = models.ForeignKey(User, related_name='supervised_trips')
    approved_by_supervisor = models.BooleanField(default=False)
    budget_owner = models.ForeignKey(User, related_name='budgeted_trips')
    approved_by_budget_owner = models.BooleanField(default=False)
    approved_by_human_resources = models.BooleanField(default=False)
    representative_approval = models.BooleanField(default=False)
    approved_date = models.DateField(blank=True, null=True)
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-from_date', '-to_date']

    def __unicode__(self):
        return u'{} - {}: {}'.format(
            self.from_date,
            self.to_date,
            self.purpose_of_travel
        )

    def reference(self):
        return '{}/{}'.format(
            self.created_date.year,
            self.id
        ) if self.id else None
    reference.short_description = 'Reference'

    def outstanding_actions(self):
        return self.actionpoint_set.filter(
            completed_date__isnull=True).count()

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
        if not self.approved_by_supervisor\
        or not self.approved_by_budget_owner:
            return False
        if self.requires_hr_approval\
        and not self.approved_by_human_resources:
            return False
        if self.requires_rep_approval\
        and not self.representative_approval:
            return False
        return True

    @classmethod
    def get_email_template_or_default(cls, name, instance):
        try:
            template = EmailTemplate.objects.get(name=name)
        except EmailTemplate.DoesNotExist:
            template = EmailTemplate(
                subject='Trip {}: {}'.format(
                    instance.status,
                    instance.reference
                )
            )
        return template

    @classmethod
    def send_trip_request(cls, sender, instance, created, **kwargs):
        current_site = Site.objects.get_current()
        if created:
            email_name = 'trips/trip/created'
            try:
                template = EmailTemplate.objects.get(
                    name=email_name
                )
            except EmailTemplate.DoesNotExist:
                template = EmailTemplate.objects.create(
                    name=email_name,
                    description='The email that is send to the supervisor once a new trip has been created',
                    subject="New Trip Created for {{owner_name}}",
                    content="Dear {{supervisor_name}},"
                            "\r\n\r\nA new trip has been created by {{owner_name}} and awaits your approval here:"
                            "\r\n\r\n{{url}}"
                            "\r\n\r\nThank you."
                )
            send_mail(
                instance.owner.email,
                template,
                {
                    'owner_name': instance.owner.get_full_name(),
                    'supervisor_name': instance.supervisor.get_full_name(),
                    'url': 'http://{}{}'.format(
                        current_site.domain,
                        instance.get_admin_url()
                    )
                },
                instance.supervisor.email
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
                instance.owner.email,
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
            send_mail(
                instance.owner.email,
                template,
                {
                    'trip_reference': instance.trip.reference(),
                    'url': 'http://{}{}'.format(
                        current_site.domain,
                        instance.get_admin_url()
                    )
                },
                instance.owner.email,
                instance.supervisor.email,
                instance.budget_owner.email,
                instance.travel_assistant.email,
            )

        if instance.approved_by_supervisor:
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

            if instance.ta_required and instance.programme_assistant and not instance.ta_approved:
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


post_save.connect(Trip.send_trip_request, sender=Trip)


class TravelRoutes(models.Model):

    trip = models.ForeignKey(Trip)
    date = models.DateField()
    origin = models.CharField(max_length=254)
    destination = models.CharField(max_length=254)
    depart = models.DateTimeField()
    arrive = models.DateTimeField()

    class Meta:
        verbose_name = 'Travel Route'
        verbose_name_plural = 'Travel Routes'


class ActionPoint(models.Model):

    trip = models.ForeignKey(Trip)
    description = models.CharField(max_length=254)
    due_date = models.DateField()
    persons_responsible = models.ManyToManyField(User)
    actions_taken = models.TextField(blank=True, null=True)
    completed_date = models.DateField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True)

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
                instance.owner.email,
                template,
                {
                    'trip_reference': instance.trip.reference(),
                    'url': 'http://{}{}#reporting'.format(
                        current_site.domain,
                        instance.trip.get_admin_url()
                    )
                },
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
