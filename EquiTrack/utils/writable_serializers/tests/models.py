from __future__ import absolute_import, division, print_function, unicode_literals

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models

from utils.common.models.fields import CodedGenericRelation


class GenericChild(models.Model):
    object_id = models.IntegerField()
    content_type = models.ForeignKey(ContentType)
    obj = GenericForeignKey()

    field = models.IntegerField()


class CodedGenericChild(models.Model):
    object_id = models.IntegerField()
    content_type = models.ForeignKey(ContentType)
    obj = GenericForeignKey()

    code = models.CharField(max_length=10, blank=True)

    field = models.IntegerField()


class Parent(models.Model):
    field = models.IntegerField()

    generic_children = GenericRelation(GenericChild)

    coded1_generic_children = CodedGenericRelation(CodedGenericChild, code='code1')
    coded2_generic_children = CodedGenericRelation(CodedGenericChild, code='code2')


class Child1(models.Model):
    parent = models.OneToOneField(Parent)
    field = models.IntegerField()
    field2 = models.IntegerField(null=True)


class Child2(models.Model):
    parent = models.ForeignKey(Parent, related_name='children2')
    field = models.IntegerField()
    field2 = models.IntegerField(null=True)


class Child3(models.Model):
    parent = models.ForeignKey(Parent, related_name='children3')
    field = models.IntegerField()
    field2 = models.IntegerField(unique=True)

    class Meta:
        unique_together = [['parent', 'field']]
