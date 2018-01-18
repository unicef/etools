from __future__ import absolute_import, division, print_function, unicode_literals

from django.core.exceptions import ValidationError as CoreValidationError
from django.db import ProgrammingError
from django.http import Http404
from django.utils import six

from django_fsm import can_proceed, has_transition_perm
from rest_framework import exceptions
from rest_framework.compat import is_authenticated
from rest_framework.decorators import detail_route
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.serializers import Serializer


class MultiSerializerViewSetMixin(object):
    serializer_action_classes = {}

    def get_serializer_class(self):
        try:
            return self.serializer_action_classes[self.action]
        except (KeyError, AttributeError):
            return super(MultiSerializerViewSetMixin, self).get_serializer_class()


class ExportViewSetDataMixin(object):
    export_serializer_class = None
    allowed_formats = ['csv', ]
    export_filename = ''

    def get_export_filename(self, format=None):
        return self.export_filename + '.' + (format or '').lower()

    def get_export_serializer_class(self, export_format=None):
        if isinstance(self.export_serializer_class, Serializer):
            return self.export_serializer_class

        if isinstance(self.export_serializer_class, dict):
            serializer_class = self.export_serializer_class.get(
                export_format,
                self.export_serializer_class['default']
            )
            if not serializer_class:
                raise KeyError
            return serializer_class

        return self.export_serializer_class

    def get_serializer_class(self):
        if self.request.method == "GET":
            query_params = self.request.query_params
            export_format = query_params.get('format')
            if export_format and self.export_serializer_class:
                return self.get_export_serializer_class(export_format=export_format)
        return super(ExportViewSetDataMixin, self).get_serializer_class()

    def dispatch(self, request, *args, **kwargs):
        response = super(ExportViewSetDataMixin, self).dispatch(request, *args, **kwargs)
        if self.request.method == "GET" and 'format' in self.request.query_params:
            response['Content-Disposition'] = "attachment;filename={}".format(
                self.get_export_filename(format=self.request.query_params.get('format'))
            )
        return response


class FSMTransitionActionMixin(object):
    @detail_route(methods=['post'], url_path='(?P<action>\D+)')
    def transition(self, request, *args, **kwargs):
        """
        Change status of the Engagement
        """
        action = kwargs.get('action', False)
        instance = self.get_object()
        instance_action = getattr(instance, action, None)
        if not instance_action or not hasattr(instance_action, '_django_fsm'):
            raise Http404

        try:
            if not can_proceed(instance_action) or not has_transition_perm(instance_action, request.user):
                raise PermissionDenied
        except CoreValidationError as ex:
            raise ValidationError(dict([error for error in ex]))

        fsm_meta = instance_action._django_fsm
        field_name = fsm_meta.field if isinstance(fsm_meta.field, six.string_types) else fsm_meta.field.name
        transition_serializer = fsm_meta.get_transition(getattr(instance, field_name)).custom.get('serializer')
        if transition_serializer:
            serializer = transition_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            instance_action(**serializer.validated_data)
        else:
            instance_action()

        instance.save()

        return self.retrieve(request, *args, **kwargs)


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
