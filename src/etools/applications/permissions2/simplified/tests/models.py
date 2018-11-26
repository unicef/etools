from django.db import models


class Parent(models.Model):
    test_field = models.CharField(max_length=10)


class Child(models.Model):
    parent = models.ForeignKey(Parent, related_name='children')
    test_field = models.CharField(max_length=10)
