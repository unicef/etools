
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import ugettext_lazy as _

from etools.applications.utils.common.models.fields import CodedGenericRelation


class CodedGenericChild(models.Model):
    field = models.IntegerField()

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.IntegerField()

    code = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name_plural = _('Coded Generic Children')
        app_label = 'tests'


class Parent(models.Model):
    field = models.IntegerField()

    children1 = CodedGenericRelation(CodedGenericChild, code='children1')
    children2 = CodedGenericRelation(CodedGenericChild, code='children2')


class Child1(models.Model):
    field = models.IntegerField()

    parent = models.ForeignKey(Parent, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = _('Children1')
        app_label = 'tests'
