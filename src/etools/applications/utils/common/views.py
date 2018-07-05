
from django.core.exceptions import ValidationError as CoreValidationError
from django.db import ProgrammingError
from django.http import Http404, QueryDict

from django_fsm import can_proceed, has_transition_perm
from rest_framework import exceptions
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
        if self.request.method == "GET" and 'format' in self.request.query_params.keys():
            response['Content-Disposition'] = "attachment;filename={}".format(
                self.get_export_filename(format=self.request.query_params.get('format'))
            )
        return response


class FSMTransitionActionMixin(object):
    def get_transition(self, action, instance=None):
        if not instance:
            instance = self.get_object()

        instance_action = getattr(instance, action, None)
        if not instance_action or not hasattr(instance_action, '_django_fsm'):
            raise Http404

        return instance_action

    def check_transition_permission(self, transition, user):
        try:
            if not can_proceed(transition) or not has_transition_perm(transition, user):
                raise PermissionDenied
        except CoreValidationError as exc:
            raise ValidationError(dict([error for error in exc]))

    def get_transition_serializer_class(self, transition):
        fsm_meta = transition._django_fsm
        im_self = getattr(transition, 'im_self', getattr(transition, '__self__'))
        current_state = fsm_meta.field.get_state(im_self)
        return fsm_meta.get_transition(current_state).custom.get('serializer')

    @detail_route(methods=['post'], url_path='(?P<action>\D+)')
    def transition(self, request, *args, **kwargs):
        """
        Change status of FSM controlled object
        """
        action = kwargs.get('action', False)
        instance = self.get_object()
        instance_action = self.get_transition(action, instance)

        self.check_transition_permission(instance_action, request.user)

        transition_serializer = self.get_transition_serializer_class(instance_action)
        if transition_serializer:
            serializer = transition_serializer(data=request.data, context=self.get_serializer_context())
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

    def get_parent_filter(self):
        return None

    def _get_parent_filters(self):
        parents = self._get_parents()

        filters = {}

        child = self
        lookups = []
        for parent in parents:
            lookups.append(child.parent_lookup_field)

            parent_filter = None
            if isinstance(child, NestedViewSetMixin):
                parent_filter = child.get_parent_filter()

            if parent_filter is None:
                parent_filter = {
                    '{}__{}'.format(
                        '__'.join(lookups), getattr(child.parent, 'lookup_field', 'pk')
                    ): self.kwargs.get(child.parent_lookup_kwarg)
                }

            filters.update(parent_filter)
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
