
from etools.applications.t2f.filters import BaseFilterBoxFilter, BaseSearchFilter, BaseSortFilter
from etools.applications.t2f.serializers.filters.action_points import (ActionPointFilterBoxSerializer,
                                                                       ActionPointSortFilterSerializer,)


class ActionPointSearchFilter(BaseSearchFilter):
    _search_fields = ('action_point_number', 'travel__reference_number', 'description')


class ActionPointSortFilter(BaseSortFilter):
    serializer_class = ActionPointSortFilterSerializer


class ActionPointFilterBoxFilter(BaseFilterBoxFilter):
    serializer_class = ActionPointFilterBoxSerializer
