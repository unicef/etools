from __future__ import absolute_import

__author__ = 'jcranwellward'

from django.db import models


class SupplyItem(models.Model):
    """
    Represents a supply item
    """

    name = models.CharField(
        max_length=255,
        unique=True
    )
    description = models.TextField(
        blank=True
    )

    def __unicode__(self):
        return self.name
