
from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class Comment(models.Model):
    author = models.ForeignKey(User, related_name='+')
    tagged_users = models.ManyToManyField(User, blank=True, related_name='+')
    timestamp = models.DateTimeField(auto_now_add=True)
    text = models.TextField()

    # This model will have relations to multiple other models. One FK would not be enough
    content_type = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')