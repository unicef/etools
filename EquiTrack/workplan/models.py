
from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType

from reports.models import ResultStructure


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
        ("On Track", "On Track"),
        ("Constrained", "Constrained"),
        ("No Progress", "No Progress"),
        ("Target Met", "Target Met"),
    )
    status = models.CharField(max_length=32, null=True, blank=True, choices=STATUS)
    comments = GenericRelation(Comment)
    result_structure = models.ForeignKey(ResultStructure)


class CoverPage(models.Model):
    # TODO if the workplan project model will be added, uncomment this and finish the args
    # workplan_project = models.OneToOneField('WorkplanProject', related_name='cover_page')

    national_priority = models.CharField(max_length=255)
    responsible_government_entity = models.CharField(max_length=255)
    planning_assumptions = models.TextField()

    logo = models.ImageField()


class CoverPageBudget(models.Model):
    cover_page = models.ForeignKey('CoverPage', related_name='budgets')

    date = models.CharField(max_length=64)
    total_amount = models.CharField(max_length=64)
    funded_amount = models.CharField(max_length=64)
    unfunded_amount = models.CharField(max_length=64)