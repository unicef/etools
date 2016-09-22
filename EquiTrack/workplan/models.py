
from django.db import models


class Quarter(models.Model):
    name = models.CharField(max_length=64)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()