from __future__ import absolute_import, division, print_function, unicode_literals

from django.db import ProgrammingError

from rest_framework import exceptions
from rest_framework.compat import is_authenticated


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

    def _get_parents(self):
        parents = []

        try:
            parent = self.parent
            if parent:
                parents.append(parent)
                parents.extend(parent()._get_parents())
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

    def get_parent_object(self):
        parent_class = getattr(self, 'parent', None)
        if not parent_class:
            return

        parent = parent_class(
            request=self.request, kwargs=self.kwargs, lookup_url_kwarg=self.parent_lookup_kwarg
        )

        return parent.get_object()

    def get_root_object(self):
        parents = self._get_parents()
        if not parents:
            return

        pre_root = parents[-2] if len(parents) > 1 else self
        root = parents[-1](
            request=self.request, kwargs=self.kwargs, lookup_url_kwarg=pre_root.parent_lookup_kwarg
        )

        return root.get_object()

    def filter_queryset(self, queryset):
        queryset = super(NestedViewSetMixin, self).filter_queryset(queryset)
        queryset = queryset.filter(**self._get_parent_filters())
        return queryset


class SafeTenantViewSetMixin(object):
    def dispatch(self, request, *args, **kwargs):
        try:
            return super(SafeTenantViewSetMixin, self).dispatch(request, *args, **kwargs)
        except ProgrammingError:
            if request.user and not is_authenticated(request.user):
                raise exceptions.NotAuthenticated()
            raise
