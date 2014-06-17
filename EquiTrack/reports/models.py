__author__ = 'jcranwellward'

from django.db import models


class ResultStructure(models.Model):
    name = models.CharField(max_length=150)

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name


class Sector(models.Model):

    name = models.CharField(max_length=45L, unique=True)
    description = models.CharField(max_length=256L, blank=True, null=True)

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name


class RRPObjective(models.Model):

    result_structure = models.ForeignKey(ResultStructure, blank=True, null=True)
    sector = models.ForeignKey(Sector)
    name = models.CharField(max_length=256L)

    class Meta:
        ordering = ['name']
        verbose_name = 'Objective'


class Rrp5Output(models.Model):

    result_structure = models.ForeignKey(ResultStructure, blank=True, null=True)
    sector = models.ForeignKey(Sector)
    objective = models.ForeignKey(RRPObjective, blank=True, null=True)
    name = models.CharField(max_length=256L)

    class Meta:
        verbose_name = 'Output'
        unique_together = ('result_structure', 'name')
        ordering = ['name']

    def __unicode__(self):
        return u'({}) {}'.format(self.result_structure, self.name)


class Goal(models.Model):

    result_structure = models.ForeignKey(ResultStructure, blank=True, null=True)
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

    def __unicode__(self):
        return self.type


class Indicator(models.Model):

    sector = models.ForeignKey(Sector)
    result_structure = models.ForeignKey(ResultStructure, blank=True, null=True)
    name = models.CharField(max_length=128L, unique=True)
    unit = models.ForeignKey(Unit)
    total = models.IntegerField(verbose_name='Target')
    view_on_dashboard = models.BooleanField(default=False)
    in_activity_info = models.BooleanField(default=False)
    activity_info_indicators = models.ManyToManyField(
        'activityinfo.Indicator',
        blank=True, null=True
    )

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return u'({}) {} {}'.format(
            self.result_structure,
            self.name,
            'ActivityInfo' if self.in_activity_info else ''
        )

    @property
    def programmed(self):
        total = self.indicatorprogress_set.aggregate(models.Sum('programmed'))
        return total[total.keys()[0]] or 0


class IntermediateResult(models.Model):
    sector = models.ForeignKey(Sector)
    ir_wbs_reference = models.CharField(max_length=50L)
    name = models.CharField(max_length=128L, unique=True)

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name


class WBS(models.Model):
    Intermediate_result = models.ForeignKey(IntermediateResult)
    name = models.CharField(max_length=128L, unique=True)
    code = models.CharField(max_length=10L)

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name


class Activity(models.Model):
    sector = models.ForeignKey(Sector)
    name = models.CharField(max_length=128L, unique=True)
    type = models.CharField(max_length=30L, blank=True, null=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Activities'

    def __unicode__(self):
        return self.name