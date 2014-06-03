__author__ = 'jcranwellward'

from django.db import models
from django.contrib.contenttypes.generic import GenericRelation

from locations.models import LinkedLocation


class TripReport(models.Model):

    TRIP_STATUS = (
        (u'planned', u"Planned"),
        (u'approved', u"Approved"),
        (u'completed', u"Completed"),
        (u'cancelled', u"Cancelled"),
    )

    purpose_of_travel = models.CharField(max_length=254)
    activities_to_undertake = models.CharField(max_length=254)
    from_date = models.DateField()
    to_date = models.DateField()
    pcas = models.ManyToManyField(u'partners.PCA', verbose_name=u"Related PCAs")
    supervisor = models.ForeignKey(u'auth.User')
    status = models.CharField(max_length=32L, choices=TRIP_STATUS, default=u'planned')
    approved_date = models.DateField(blank=True, null=True)

    main_observations = models.TextField(blank=True, null=True)
    locations = GenericRelation(LinkedLocation)

    class Meta:
        ordering = ['from_date', 'to_date']

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

    class Meta:
        verbose_name = 'Travel Route'
        verbose_name_plural = 'Travel Routes'


class ActionPoint(models.Model):

    trip_report = models.ForeignKey(TripReport)
    description = models.CharField(max_length=254)
    due_date = models.DateField()
    person_responsible = models.ForeignKey(u'auth.User')
    completed_date = models.DateField(blank=True, null=True)
