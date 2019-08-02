from django.db import models
from django.utils.translation import ugettext_lazy as _

from model_utils import Choices


class PSEARatingField(models.CharField):

    HIGH = 'high'
    MEDIUM = 'medium'
    LOW = 'low'

    RATING = Choices(
        (HIGH, _('High')),
        (MEDIUM, _('Medium')),
        (LOW, _('Low')),
    )

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = kwargs.get('max_length', 8)
        kwargs['choices'] = self.RATING
        kwargs['null'] = kwargs.get('null', True)
        kwargs['blank'] = kwargs.get('blank', True)
        super().__init__(*args, **kwargs)
