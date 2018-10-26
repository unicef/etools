from datetime import date

from django.http import Http404
from django.utils.translation import ugettext_lazy as _

from rest_framework import mixins, viewsets

from etools.applications.field_monitoring.planning.models import YearPlan
from etools.applications.field_monitoring.planning.serializers import YearPlanSerializer, YearPlanAttachmentSerializer
from etools.applications.field_monitoring.views import FMBaseViewSet, BaseFMAttachmentsViewSet


class YearPlanViewSet(
    FMBaseViewSet,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    queryset = YearPlan.objects.all()
    serializer_class = YearPlanSerializer

    def get_years_allowed(self):
        return map(str, [date.today().year, date.today().year + 1])

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        return queryset.filter(year__in=self.get_years_allowed())

    def get_object(self):
        """ get or create object for specified year. only current & next are allowed"""

        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        if self.kwargs[lookup_url_kwarg] not in self.get_years_allowed():
            raise Http404

        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}

        obj = queryset.get_or_create(**filter_kwargs)[0]

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj


class YearPlanAttachmentsViewSet(BaseFMAttachmentsViewSet):
    serializer_class = YearPlanAttachmentSerializer
    related_model = YearPlan

    def get_view_name(self):
        return _('Attachments')
