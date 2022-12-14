from django.conf import settings
from django.contrib.auth import logout
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import RedirectView

import jwt
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from etools.applications.core.permissions import IsUNICEFUser


class MainView(RedirectView):
    url = settings.LOGIN_URL

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(request.GET.get('next', 'dashboard'))

        return super().get(request, *args, **kwargs)


class IssueJWTRedirectView(APIView):
    permission_classes = (IsUNICEFUser, )

    def get(self, request):
        user = self.request.user

        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)

        decoded_token = jwt.decode(access,
                                   settings.SIMPLE_JWT['VERIFYING_KEY'],
                                   [settings.SIMPLE_JWT['ALGORITHM']],
                                   audience=settings.SIMPLE_JWT['AUDIENCE'],
                                   leeway=settings.SIMPLE_JWT['LEEWAY'],
                                   )

        decoded_token.update({
            'groups': list(user.groups.values_list('name', flat=True)),
            'username': user.username,
            'email': user.email,
        })

        encoded = jwt.encode(
            decoded_token,
            settings.SIMPLE_JWT['SIGNING_KEY'],
            algorithm=settings.SIMPLE_JWT['ALGORITHM']
        )

        return Response(data={'token': encoded})


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("main"))


class SocialLogoutView(RedirectView):

    def get_redirect_url(self, *args, **kwargs):
        return settings.SOCIAL_LOGOUT_URL
