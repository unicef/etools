from django.core.exceptions import ValidationError as CoreValidationError
from django.http import Http404

from django_fsm import can_proceed, has_transition_perm
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.serializers import Serializer


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

    def pre_transition(self, instance, action):
        """
        hook to implement custom logic before transition
        """
        pass

    def post_transition(self, instance, action):
        """
        hook to implement custom logic after transition
        """
        pass

    @action(detail=True, methods=['post'], url_path='(?P<action>\D+)')
    def transition(self, request, *args, **kwargs):
        """
        Change status of FSM controlled object
        """
        action = kwargs.get('action', False)
        instance = self.get_object()
        instance_action = self.get_transition(action, instance)

        self.pre_transition(instance, action)

        self.check_transition_permission(instance_action, request.user)

        transition_serializer = self.get_transition_serializer_class(instance_action)
        if transition_serializer:
            serializer = transition_serializer(data=request.data, context=self.get_serializer_context())
            serializer.is_valid(raise_exception=True)
            instance_action(**serializer.validated_data)
        else:
            instance_action()

        instance.save()

        self.post_transition(instance, action)

        return self.retrieve(request, *args, **kwargs)
