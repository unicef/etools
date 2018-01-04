from __future__ import absolute_import, division, print_function, unicode_literals

import decimal
import json
from datetime import datetime

from django.contrib.postgres.fields import JSONField
from django.db import models

from model_utils.models import TimeStampedModel

from EquiTrack.utils import get_current_year
from partners.models import PartnerOrganization


class HactEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        elif isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)


class HactHistory(TimeStampedModel):

    partner = models.ForeignKey(PartnerOrganization, related_name='related_partner')
    year = models.IntegerField(default=get_current_year)
    partner_values = JSONField(null=True, blank=True)

    class Meta:
        unique_together = ('partner', 'year')
