__author__ = 'jcranwellward'

from django.db import models


class Donor(models.Model):
    name = models.CharField(max_length=45L, unique=True)

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name


class Grant(models.Model):

    donor = models.ForeignKey(Donor)
    name = models.CharField(max_length=128L, unique=True)
    expiry = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['donor']

    def __unicode__(self):
        return u"{}: {}".format(
            self.donor.name,
            self.name
        )
