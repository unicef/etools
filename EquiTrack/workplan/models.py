
from django.contrib.auth.models import User
from django.db import models


class Comment(models.Model):
    author = models.ForeignKey(User, related_name='+')
    tagged_users = models.ManyToManyField(User, blank=True, null=True, related_name='+')
    timestamp = models.DateTimeField(auto_now_add=True)
    text = models.TextField()