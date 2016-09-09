from jsonfield import JSONField
from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType

from users.models import Section
from locations.models import Location
from partners.models import PartnerOrganization
from reports.models import ResultStructure, ResultType


class Comment(models.Model):
    author = models.ForeignKey(User, related_name='+')
    tagged_users = models.ManyToManyField(User, blank=True, related_name='+')
    timestamp = models.DateTimeField(auto_now_add=True)
    text = models.TextField()

    # This model will have relations to multiple other models. One FK would not be enough
    content_type = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')


class Workplan(models.Model):
    STATUS = (
        ("Draft", "Draft"),
        ("Approved", "Approved"),
        ("Completed", "Completed"),
    )
    status = models.CharField(max_length=32, null=True, blank=True, choices=STATUS)
    comments = GenericRelation(Comment)
    result_structure = models.ForeignKey(ResultStructure)


class Label(models.Model):
    name = models.CharField(max_length=32)


class ResultWorkplanProperty(models.Model):
    workplan = models.ForeignKey(Workplan)
    result_type = models.ForeignKey(ResultType)
    assumptions = models.TextField(null=True, blank=True)
    STATUS = (
        ("On Track","On Track"),
        ("Constrained","Constrained"),
        ("No Progress","No Progress"),
        ("Target Met","Target Met"),
    )
    status = models.CharField(max_length=255, null=True, blank=True, choices=STATUS)
    prioritized = models.BooleanField(default=False)
    metadata = JSONField(null=True, blank=True)
    other_partners = models.CharField(max_length=2048, null=True, blank=True)
    rr_funds = models.PositiveIntegerField(null=True, blank=True)
    or_funds = models.PositiveIntegerField(null=True, blank=True)
    ore_funds = models.PositiveIntegerField(null=True, blank=True)
    total_funds = models.PositiveIntegerField(null=True, blank=True)
    sections = models.ManyToManyField(Section)
    geotag = models.ManyToManyField(Location)
    partners = models.ManyToManyField(PartnerOrganization)
    responsible_persons = models.ManyToManyField(User)
    labels = models.ManyToManyField(Label)

    def save(self, *args, **kwargs):
        """
        Override save to calculate field total
        """
        self.total_funds = self.rr_funds + self.or_funds + self.ore_funds
        super(ResultWorkplanProperty, self).save(*args, **kwargs)

    @classmethod
    def has_label(cls, label_id):
        """
        Determines if a given Label is used across ResultWorkplanProperty instances.

        Args:
            label_id: id of the given Label

        Return:
            bool: True if used, False if not
        """
        return cls.objects.filter(labels__id=label_id).exists()
