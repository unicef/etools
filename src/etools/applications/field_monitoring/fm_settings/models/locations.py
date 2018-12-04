from django.contrib.gis.db.models import PointField
from django.db import models
from django.utils.translation import ugettext_lazy as _
from model_utils import FieldTracker

from model_utils.models import TimeStampedModel

from unicef_locations.models import Location


class LocationSite(TimeStampedModel):
    parent = models.ForeignKey(
        Location,
        verbose_name=_("Parent Location"),
        related_name='sites',
        db_index=True,
        on_delete=models.CASCADE
    )
    name = models.CharField(verbose_name=_("Name"), max_length=254)
    p_code = models.CharField(
        verbose_name=_("P Code"),
        max_length=32,
        blank=True,
        default='',
    )

    point = PointField(verbose_name=_("Point"), null=True, blank=True)
    is_active = models.BooleanField(verbose_name=_("Active"), default=True, blank=True)

    security_detail = models.TextField(verbose_name=_('Detail on Security'), blank=True)

    tracker = FieldTracker(['point'])

    class Meta:
        verbose_name = _('Location Site')
        verbose_name_plural = _('Location Sites')
        ordering = ('parent', 'id',)

    def __str__(self):
        return u'{}: {}'.format(
            self.name,
            self.p_code if self.p_code else ''
        )

    @staticmethod
    def get_parent_location(point):
        matched_locations = Location.objects.filter(geom__contains=point)
        if not matched_locations:
            location = Location.objects.filter(gateway__admin_level=0).first()
        else:
            leafs = filter(lambda l: l.is_leaf_node(), matched_locations)
            location = min(leafs, key=lambda l: l.geom.length)

        return location

    def save(self, **kwargs):
        if not self.parent_id:
            self.parent = self.get_parent_location(self.point)
            assert self.parent_id, 'Unable to find location for {}'.format(self.point)
        elif self.tracker.has_changed('point'):
            self.parent = self.get_parent_location(self.point)

        super().save(**kwargs)
