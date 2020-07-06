from django.conf import settings
from django.contrib.auth import logout
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import RedirectView

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_jwt.serializers import jwt_encode_handler, jwt_payload_handler
from rest_framework_jwt.views import jwt_response_payload_handler


class MainView(RedirectView):
    url = settings.LOGIN_URL

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(request.GET.get('next', 'dashboard'))

        return super().get(request, *args, **kwargs)


class IssueJWTRedirectView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = self.request.user
        payload = jwt_payload_handler(user)
        token = jwt_encode_handler(payload)
        response_data = jwt_response_payload_handler(token, user, request)

        return Response(data=response_data)


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("main"))
