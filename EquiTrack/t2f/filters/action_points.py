from __future__ import unicode_literals

from t2f.filters import BaseSearchFilter, BaseSortFilter, BaseFilterBoxFilter

from t2f.serializers.filters.action_points import ActionPointSortFilterSerializer, ActionPointFilterBoxSerializer


class ActionPointSearchFilter(BaseSearchFilter):
    _search_fields = ('action_point_number', 'travel__reference_number', 'description')


class ActionPointSortFilter(BaseSortFilter):
    serializer_class = ActionPointSortFilterSerializer


class ActionPointFilterBoxFilter(BaseFilterBoxFilter):
    serializer_class = ActionPointFilterBoxSerializer
