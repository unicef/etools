from django.contrib.postgres.fields import JSONField
from django.db import models
from django.contrib.auth.models import User
from model_utils.models import TimeStampedModel

from users.models import Section
from locations.models import Location
from partners.models import PartnerOrganization
from reports.models import Result


class Comment(TimeStampedModel):
    """
    Represents a comment

    Relates to :model:`auth.User`
    Relates to :model:`workplan.Workplan`
    """

    author = models.ForeignKey(User, related_name='comments')
    tagged_users = models.ManyToManyField(User, blank=True, related_name='+')
    text = models.TextField()
    workplan = models.ForeignKey('Workplan', related_name='comments')


class Workplan(models.Model):
    """
    Represents a work plan for the country programme

    Relates to :model:`reports.CountryProgramme`
    """

    STATUS = (
        ("On Track", "On Track"),
        ("Constrained", "Constrained"),
        ("No Progress", "No Progress"),
        ("Target Met", "Target Met"),
    )
    status = models.CharField(max_length=32, null=True, blank=True, choices=STATUS)
    country_programme = models.ForeignKey('reports.CountryProgramme')


class WorkplanProject(models.Model):
    """
    Represents a project for the work plan

    Relates to :model:`workplan.Workplan`
    """

    workplan = models.ForeignKey('Workplan', related_name='workplan_projects')
    # TODO: add all results that belong to this workplan project


class Quarter(models.Model):
    """
    Represents a quarter for the work plan

    Relates to :model:`workplan.Workplan`
    """

    workplan = models.ForeignKey('Workplan', related_name='quarters')
    name = models.CharField(max_length=64)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()


class Label(models.Model):
    """
    Represents a label
    """

    name = models.CharField(max_length=32, unique=True)


class ResultWorkplanProperty(models.Model):
    """
    Represents a result work plan property for the work plan

    Relates to :model:`workplan.Workplan`
    Relates to :model:`reports.Result`
    Relates to :model:`users.Section`
    Relates to :model:`locations.Location`
    Relates to :model:`partners.PartnerOrganization`
    Relates to :model:`auth.User`
    Relates to :model:`workplan.Label`
    """

    workplan = models.OneToOneField(Workplan)
    result = models.ForeignKey(Result, related_name='workplan_properties')
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
    sections = models.ManyToManyField(Section, related_name="sections+")
    geotag = models.ManyToManyField(Location, related_name="geotag+")
    partners = models.ManyToManyField(PartnerOrganization, related_name="partners+")
    responsible_persons = models.ManyToManyField(User, related_name="responsible_persons+")
    labels = models.ManyToManyField(Label)

    def save(self, *args, **kwargs):
        """
        Override save to calculate field total
        """
        if not(self.rr_funds is None and
               self.or_funds is None and
               self.ore_funds is None):

            rr_f = self.rr_funds or 0
            or_f = self.or_funds or 0
            ore_f = self.ore_funds or 0
            self.total_funds = rr_f + or_f + ore_f
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


class CoverPage(models.Model):
    """
    Represents a cover page for the work plan project

    Relates to :model:`workplan.WorkplanProject`
    """

    workplan_project = models.OneToOneField('WorkplanProject', related_name='cover_page')

    national_priority = models.CharField(max_length=255)
    responsible_government_entity = models.CharField(max_length=255)
    planning_assumptions = models.TextField()
    logo = models.ImageField(width_field='logo_width', height_field='logo_height', null=True, blank=True)


class CoverPageBudget(models.Model):
    """
    Represents a budget for the cover page

    Relates to :model:`workplan.CoverPage`
    """
    cover_page = models.ForeignKey('CoverPage', related_name='budgets')

    from_date = models.DateField()
    to_date = models.DateField()
    total_amount = models.CharField(max_length=64)
    funded_amount = models.CharField(max_length=64)
    unfunded_amount = models.CharField(max_length=64)
