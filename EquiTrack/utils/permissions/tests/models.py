from django.db import models

from model_utils import Choices

from utils.permissions.models.models import BasePermission


class Parent(models.Model):
    field = models.IntegerField()


class Child2(models.Model):
    parent = models.ForeignKey(Parent, related_name='children2')
    field = models.IntegerField()
    field2 = models.IntegerField(null=True)


class Permission(BasePermission):
    USER_TYPES = Choices(
        'Group1',
        'Group2',
    )
