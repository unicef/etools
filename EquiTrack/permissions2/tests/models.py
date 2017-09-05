from django.db import models


class Parent(models.Model):
    field1 = models.IntegerField()
    field2 = models.IntegerField(null=True)


class Child1(models.Model):
    parent = models.ForeignKey(Parent, related_name='children1')
    field1 = models.IntegerField()
    field2 = models.IntegerField(null=True)
