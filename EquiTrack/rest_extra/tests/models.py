from __future__ import absolute_import, division, print_function, unicode_literals

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import ugettext_lazy as _

from generics.fields import CodedGenericRelation


class GenericChild(models.Model):
    object_id = models.IntegerField()
    content_type = models.ForeignKey(ContentType, related_name='generic_child')
    obj = GenericForeignKey()

    field = models.IntegerField()

    class Meta:
        verbose_name_plural = _('Generic Children')


class CodedGenericChild(models.Model):
    object_id = models.IntegerField()
    content_type = models.ForeignKey(ContentType, related_name='coded_generic_child')
    obj = GenericForeignKey()

    code = models.CharField(max_length=10, blank=True)

    field = models.IntegerField()

    class Meta:
        verbose_name_plural = _('Coded Generic Children')


class Parent(models.Model):
    field = models.IntegerField()

    generic_children = GenericRelation(GenericChild)

    coded1_generic_children = CodedGenericRelation(CodedGenericChild, code='code1')
    coded2_generic_children = CodedGenericRelation(CodedGenericChild, code='code2')


class Child1(models.Model):
    parent = models.OneToOneField(Parent)
    field = models.IntegerField()
    field2 = models.IntegerField(null=True)

    class Meta:
        verbose_name_plural = _('Children1')


class Child2(models.Model):
    parent = models.ForeignKey(Parent, related_name='children2')
    field = models.IntegerField()
    field2 = models.IntegerField(null=True)

    class Meta:
        verbose_name_plural = _('Children2')


class Child3(models.Model):
    parent = models.ForeignKey(Parent, related_name='children3')
    field = models.IntegerField()
    field2 = models.IntegerField(unique=True)

    class Meta:
        unique_together = [['parent', 'field']]
        verbose_name_plural = _('Children3')


class Child4(models.Model):
    field = models.IntegerField()
    parent = models.ForeignKey(Parent)
