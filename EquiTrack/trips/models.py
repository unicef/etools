__author__ = 'jcranwellward'

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import (
    GenericForeignKey, GenericRelation
)

from filer.fields.file import FilerFileField

from locations.models import LinkedLocation

User = get_user_model()


class TripReport(models.Model):

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

    purpose_of_travel = models.CharField(max_length=254)
    travel_type = models.CharField(max_length=32L, choices=TRAVEL_TYPE, default=DUTY_TRAVEL)
    international_travel = models.BooleanField(default=False)
    from_date = models.DateField()
    to_date = models.DateField()

    status = models.CharField(max_length=32L, choices=TRIP_STATUS, default=PLANNED)
    supervisor = models.ForeignKey(u'auth.User')
    budget_owner = models.ForeignKey(u'auth.User')
    human_resources = models.ForeignKey(u'auth.User', blank=True, null=True)
    representative_approval = models.BooleanField(default=False)
    approved_date = models.DateField(blank=True, null=True)

    activities_undertaken = models.CharField(max_length=254, verbose_name='Activities')
    no_pca = models.BooleanField(verbose_name=u'Not related to a PCA', default=False)
    pcas = models.ManyToManyField(u'partners.PCA', verbose_name=u"Related PCAs")
    partners = models.ManyToManyField(u'partners.PartnerOrganization', blank=True, null=True)
    main_observations = models.TextField(blank=True, null=True)
    locations = GenericRelation(LinkedLocation)

    class Meta:
        ordering = ['-from_date', '-to_date']

    def __unicode__(self):
        return u'{} - {}: {}'.format(
            self.from_date,
            self.to_date,
            self.purpose_of_travel
        )


class TravelRoutes(models.Model):

    trip_report = models.ForeignKey(TripReport)
    date = models.DateField()
    route = models.CharField(max_length=254)
    depart = models.TimeField()
    arrive = models.TimeField()

    class Meta:
        verbose_name = 'Travel Route'
        verbose_name_plural = 'Travel Routes'


class ActionPoint(models.Model):

    trip_report = models.ForeignKey(TripReport)
    description = models.CharField(max_length=254)
    due_date = models.DateField()
    persons_responsible = models.ManyToManyField(User)
    completed_date = models.DateField(blank=True, null=True)


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