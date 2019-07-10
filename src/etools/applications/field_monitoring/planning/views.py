from datetime import date

from django.http import Http404
from django.utils.translation import ugettext_lazy as _
from rest_framework import viewsets, mixins

from etools.applications.field_monitoring.permissions import IsReadAction, IsEditAction, UserIsFieldMonitor
from etools.applications.field_monitoring.planning.models import YearPlan
from etools.applications.field_monitoring.planning.serializers import YearPlanSerializer
from etools.applications.field_monitoring.views import FMBaseViewSet
from etools.applications.permissions_simplified.permissions import PermissionQ as Q


class YearPlanViewSet(
    FMBaseViewSet,
    # SimplePermittedViewSetMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet
):
    permission_classes = FMBaseViewSet.permission_classes + [
        Q(IsReadAction) | (Q(IsEditAction) & Q(UserIsFieldMonitor))
    ]
    # write_permission_classes = [UserIsFieldMonitor]
    # metadata_class = SimplePermissionBasedMetadata
    queryset = YearPlan.objects.all()
    serializer_class = YearPlanSerializer

    def get_view_name(self):
        return _('Annual Field Monitoring Rationale')

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

        defaults = YearPlan.get_defaults(self.kwargs[lookup_url_kwarg])
        obj = queryset.get_or_create(**filter_kwargs, defaults=defaults)[0]

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj
