from django.shortcuts import redirect
from django.views.generic import TemplateView

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_jwt.serializers import jwt_encode_handler, jwt_payload_handler
from rest_framework_jwt.views import jwt_response_payload_handler


class MainView(TemplateView):
    template_name = 'choose_login.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(request.GET.get('next', 'dashboard'))

        return super().get(request, *args, **kwargs)


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
