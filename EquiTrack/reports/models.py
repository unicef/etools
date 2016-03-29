__author__ = 'jcranwellward'

from django.db import models

from mptt.models import MPTTModel, TreeForeignKey
from paintstore.fields import ColorPickerField
from model_utils.models import (
    TimeFramedModel,
    TimeStampedModel,
)


# TODO: move to the global schema
class ResultStructure(models.Model):

    name = models.CharField(max_length=150)
    from_date = models.DateField()
    to_date = models.DateField()

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name

    @classmethod
    def current(cls):
        return ResultStructure.objects.order_by('to_date').last()


class ResultType(models.Model):

    name = models.CharField(max_length=150)

    def __unicode__(self):
        return self.name


class Sector(models.Model):

    name = models.CharField(max_length=45L, unique=True)
    description = models.CharField(
        max_length=256L,
        blank=True,
        null=True
    )
    alternate_id = models.IntegerField(
        blank=True,
        null=True
    )
    alternate_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    dashboard = models.BooleanField(
        default=False
    )
    color = ColorPickerField(null=True, blank=True)

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return u'{} {}'.format(
            self.alternate_id if self.alternate_id else '',
            self.name
        )


class Result(MPTTModel):

    result_structure = models.ForeignKey(ResultStructure)
    result_type = models.ForeignKey(ResultType)
    sector = models.ForeignKey(Sector, null=True, blank=True)
    name = models.TextField()
    code = models.CharField(max_length=50, null=True, blank=True)
    from_date = models.DateField(null=True, blank=True)
    to_date = models.DateField(null=True, blank=True)
    parent = TreeForeignKey(
        'self',
        null=True, blank=True,
        related_name='children',
        db_index=True
    )

    # activity level attributes
    humanitarian_tag = models.BooleanField(default=False)
    wbs = models.CharField(max_length=50, null=True, blank=True)
    vision_id = models.CharField(max_length=10, null=True, blank=True)
    gic_code = models.CharField(max_length=8, null=True, blank=True)
    gic_name = models.CharField(max_length=255, null=True, blank=True)
    sic_code = models.CharField(max_length=8, null=True, blank=True)
    sic_name = models.CharField(max_length=255, null=True, blank=True)
    activity_focus_code = models.CharField(max_length=8, null=True, blank=True)
    activity_focus_name = models.CharField(max_length=255, null=True, blank=True)

    hidden = models.BooleanField(default=False)
    ram = models.BooleanField(default=False)

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return u'{} {}: {}'.format(
            self.code if self.code else u'',
            self.result_type.name,
            self.name
        )

    def save(self, *args, **kwargs):

        super(Result, self).save(*args, **kwargs)
        nodes = self.get_descendants()
        for node in nodes:
            if node.hidden is not self.hidden:
                node.hidden = self.hidden
                node.save()


class Goal(models.Model):

    result_structure = models.ForeignKey(
        ResultStructure, blank=True, null=True)
    sector = models.ForeignKey(Sector, related_name='goals')
    name = models.CharField(max_length=512L, unique=True)
    description = models.CharField(max_length=512L, blank=True)

    class Meta:
        verbose_name = 'CCC'
        ordering = ['name']

    def __unicode__(self):
        return self.name


class Unit(models.Model):
    type = models.CharField(max_length=45L, unique=True)

    class Meta:
        ordering = ['type']

    def __unicode__(self):
        return self.type


class Indicator(models.Model):

    sector = models.ForeignKey(
        Sector,
        blank=True, null=True
    )
    result_structure = models.ForeignKey(
        ResultStructure,
        blank=True, null=True
    )

    result = models.ForeignKey(Result, null=True, blank=True)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, null=True, blank=True)
    unit = models.ForeignKey(Unit, null=True, blank=True)

    total = models.IntegerField(verbose_name='UNICEF Target', null=True, blank=True)
    sector_total = models.IntegerField(verbose_name='Sector Target', null=True, blank=True)
    current = models.IntegerField(null=True, blank=True, default=0)
    sector_current = models.IntegerField(null=True, blank=True)

    # RAM Info
    target = models.CharField(max_length=255, null=True, blank=True)
    baseline = models.CharField(max_length=255, null=True, blank=True)
    ram_indicator = models.BooleanField(default=False)

    view_on_dashboard = models.BooleanField(default=False)

    in_activity_info = models.BooleanField(default=False)
    activity_info_indicators = models.ManyToManyField(
        'activityinfo.Indicator',
        blank=True, null=True
    )

    class Meta:
        ordering = ['name']
        unique_together = (("name", "result", "sector"),)

    def __unicode__(self):
        return u'{} {} {}'.format(
            self.name,
            u'Baseline: {}'.format(self.baseline) if self.baseline else u'',
            u'Target: {}'.format(self.target) if self.target else u''
        )

    def programmed_amounts(self):
        from partners.models import PCA
        return self.indicatorprogress_set.filter(
            pca_sector__pca__status__in=[PCA.ACTIVE, PCA.IMPLEMENTED]
        )

    def programmed(self, result_structure=None):
        programmed = self.programmed_amounts()
        if result_structure:
            programmed = programmed.filter(
                pca_sector__pca__result_structure=result_structure,

            )
        total = programmed.aggregate(models.Sum('programmed'))
        return total[total.keys()[0]] or 0

    def progress(self, result_structure=None):
        programmed = self.programmed_amounts()
        if result_structure:
            programmed = programmed.filter(
                pca_sector__pca__result_structure=result_structure,

            )
        total = programmed.aggregate(models.Sum('current'))
        return (total[total.keys()[0]] or 0) + self.current if self.current else 0

