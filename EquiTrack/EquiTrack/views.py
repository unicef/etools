import six

from django.core.exceptions import ValidationError as CoreValidationError
from django_fsm import can_proceed, has_transition_perm
from django.http import Http404
from django.views.generic import TemplateView

from rest_framework.decorators import detail_route
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.views import APIView
from rest_framework_jwt.serializers import jwt_encode_handler, jwt_payload_handler
from rest_framework_jwt.views import jwt_response_payload_handler


class MainView(TemplateView):
    template_name = 'choose_login.html'


class OutdatedBrowserView(TemplateView):
    template_name = 'outdated_browser.html'


class IssueJWTRedirectView(APIView):
    permission_classes = ()

    def get(self, request):
        user = self.request.user
        payload = jwt_payload_handler(user)
        token = jwt_encode_handler(payload)
        response_data = jwt_response_payload_handler(token, user, request)

        return Response(data=response_data)


class FSMTransitionActionMixin(object):
    @detail_route(methods=['post'], url_path='(?P<action>\D+)')
    def transition(self, request, *args, **kwargs):
        """
        Change status of FSM controlled object
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
