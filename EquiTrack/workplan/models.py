
from django.db import models
from django.contrib.auth.models import User

from reports.models import ResultStructure


class Comment(models.Model):
    author = models.ForeignKey(User, related_name='comments')
    tagged_users = models.ManyToManyField(User, blank=True, related_name='+')
    timestamp = models.DateTimeField(auto_now_add=True)
    text = models.TextField()
    workplan = models.ForeignKey('Workplan', related_name='comments')


class Workplan(models.Model):
    STATUS = (
        ("On Track", "On Track"),
        ("Constrained", "Constrained"),
        ("No Progress", "No Progress"),
        ("Target Met", "Target Met"),
    )
    status = models.CharField(max_length=32, null=True, blank=True, choices=STATUS)
    result_structure = models.ForeignKey(ResultStructure)
