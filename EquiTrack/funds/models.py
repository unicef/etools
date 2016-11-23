__author__ = 'jcranwellward'

from django.db import models


class Donor(models.Model):
    """
    Represents Donor for a Grant.
    """

    name = models.CharField(max_length=45L, unique=True)

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name


class GrantManager(models.Manager):
    def get_queryset(self):
        return super(GrantManager, self).get_queryset().select_related('donor')


class Grant(models.Model):
    """
    Represents the name of a Grant with expiration date, and Donor name.

    Relates to :model:`funds.Donor`
    """

    donor = models.ForeignKey(Donor)
    name = models.CharField(max_length=128L, unique=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    expiry = models.DateField(null=True, blank=True)

    objects = GrantManager()

    class Meta:
        ordering = ['donor']

    def __unicode__(self):
        return u"{}: {}".format(
            self.donor.name,
            self.name
        )
