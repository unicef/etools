from django.db import ProgrammingError
from django.http import QueryDict

from rest_framework import exceptions


class MultiSerializerViewSetMixin(object):
    serializer_action_classes = {}

    def get_serializer_class(self):
        try:
            return self.serializer_action_classes[self.action]
        except (KeyError, AttributeError):
            return super(MultiSerializerViewSetMixin, self).get_serializer_class()


class NestedViewSetMixin(object):
    """
    Allow viewsets inheritance with correct filtering depending on parents.
    """

    parent = None
    parent_lookup_kwarg = None
    parent_lookup_field = None

    @classmethod
    def _get_parents(cls):
        parents = []

        try:
            parent = cls.parent
            if parent:
                parents.append(parent)
                parents.extend(parent._get_parents())
        except AttributeError:
            pass

        return parents

    def _get_parent_filters(self):
        parents = self._get_parents()

        filters = {}

        child = self
        lookups = []
        for parent in parents:
            lookups.append(child.parent_lookup_field)
            filters['{}__{}'.format(
                '__'.join(lookups), getattr(child.parent, 'lookup_field', 'pk')
            )] = self.kwargs.get(child.parent_lookup_kwarg)

            child = parent

        return filters

    def get_parent(self):
        parent_class = getattr(self, 'parent', None)
        if not parent_class:
            return

        return parent_class(
            request=self.request, kwargs=self.kwargs, lookup_url_kwarg=self.parent_lookup_kwarg
        )

    def get_parent_object(self):
        # remove request query for a while to prevent incorrect filter results for parent view
        query = self.request._request.GET
        self.request._request.GET = QueryDict()

        try:
            parent = self.get_parent()
            if not parent or not self.kwargs:
                return
            parent_object = parent.get_object()
        finally:
            self.request._request.GET = query

        return parent_object

    def get_root_object(self):
        # remove request query for a while to prevent incorrect filter results for parent view
        query = self.request._request.GET
        self.request._request.GET = QueryDict()

        try:
            parents = self._get_parents()
            if not parents:
                return

            pre_root = parents[-2] if len(parents) > 1 else self
            root = parents[-1](
                request=self.request, kwargs=self.kwargs, lookup_url_kwarg=pre_root.parent_lookup_kwarg
            )
            root_object = root.get_object()
        finally:
            self.request._request.GET = query

        return root_object

    def filter_queryset(self, queryset):
        queryset = super(NestedViewSetMixin, self).filter_queryset(queryset)
        queryset = queryset.filter(**self._get_parent_filters())
        return queryset


class SafeTenantViewSetMixin(object):
    def dispatch(self, request, *args, **kwargs):
        try:
            return super(SafeTenantViewSetMixin, self).dispatch(request, *args, **kwargs)
        except ProgrammingError:
            if request.user and not request.user.is_authenticated:
                raise exceptions.NotAuthenticated()
            raise
