
from django.db import models

from model_utils import Choices


class QuarterField(models.CharField):

    Q1 = 'q1'
    Q2 = 'q2'
    Q3 = 'q3'
    Q4 = 'q4'

    QUARTERS = Choices(
        (Q1, 'Q1'),
        (Q2, 'Q2'),
        (Q3, 'Q3'),
        (Q4, 'Q4')
    )

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = kwargs.get('max_length', 2)
        kwargs['choices'] = self.QUARTERS
        kwargs['null'] = True
        kwargs['blank'] = True
        super(models.CharField, self).__init__(*args, **kwargs)
