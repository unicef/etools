from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from model_utils import Choices

from utils.permissions.models.models import BasePermission


class GenericChild(models.Model):
    object_id = models.IntegerField()
    content_type = models.ForeignKey(ContentType)
    obj = GenericForeignKey()

    field = models.IntegerField()

    class Meta:
        app_label = 'tests'


class Parent(models.Model):
    field = models.IntegerField()

    generic_children = GenericRelation(GenericChild)

    class Meta:
        app_label = 'tests'


class Child1(models.Model):
    parent = models.OneToOneField(Parent)
    field = models.IntegerField()
    field2 = models.IntegerField(null=True)

    class Meta:
        app_label = 'tests'


class Child2(models.Model):
    parent = models.ForeignKey(Parent, related_name='children2')
    field = models.IntegerField()
    field2 = models.IntegerField(null=True)

    class Meta:
        app_label = 'tests'


class Child3(models.Model):
    parent = models.ForeignKey(Parent, related_name='children3')
    field = models.IntegerField()
    field2 = models.IntegerField(unique=True)

    class Meta:
        app_label = 'tests'
        unique_together = [['parent', 'field']]


class Permission(BasePermission):
    USER_TYPES = Choices(
        'Group1',
        'Group2',
    )

    class Meta:
        app_label = 'tests'
