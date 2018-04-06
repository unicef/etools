import logging

from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.utils import perform_login
from allauth.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.http.response import HttpResponseRedirect
from django.utils.http import urlsafe_base64_encode
import jwt
from rest_framework.authentication import BasicAuthentication, SessionAuthentication, TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework_jwt.settings import api_settings
from rest_framework_jwt.utils import jwt_payload_handler

from EquiTrack.utils import set_country

jwt_decode_handler = api_settings.JWT_DECODE_HANDLER
logger = logging.getLogger(__name__)


class DRFBasicAuthMixin(BasicAuthentication):
    def authenticate(self, request):
        super_return = super(DRFBasicAuthMixin, self).authenticate(request)
        if not super_return:
            return None

        user, token = super_return
        set_country(user, request)
        return user, token


class EtoolsTokenAuthentication(TokenAuthentication):

    def authenticate(self, request):
        super_return = super(EtoolsTokenAuthentication, self).authenticate(request)
        if not super_return:
            return None

        user, token = super_return
        set_country(user, request)
        return user, token


class EToolsTenantJWTAuthentication(JSONWebTokenAuthentication):
    """
    Handles setting the tenant after a JWT successful authentication
    """
    def authenticate(self, request):

        jwt_value = self.get_jwt_value(request)
        if jwt_value is None:
            # no JWT token return to skip this authentication mechanism
            return None

        try:
            user, jwt_value = super(EToolsTenantJWTAuthentication, self).authenticate(request)
        except TypeError:
            raise PermissionDenied(detail='No valid authentication provided')
        except AuthenticationFailed:
            # Try again
            if getattr(settings, 'JWT_ALLOW_NON_EXISTENT_USERS', False):
                try:
                    # try and see if the token is valid
                    payload = jwt_decode_handler(jwt_value)
                except (jwt.ExpiredSignature, jwt.DecodeError):
                    raise PermissionDenied(detail='Authentication Failed')
                else:
                    # signature is valid user does not exist... setting default authenticated user
                    user = get_user_model().objects.get(username=settings.DEFAULT_UNICEF_USER)
                    setattr(user, 'jwt_payload', payload)
            else:
                raise PermissionDenied(detail='Authentication Failed')

        if not user.profile.country:
            raise PermissionDenied(detail='No country found for user')

        if user.profile.country_override and user.profile.country != user.profile.country_override:
            user.profile.country = user.profile.country_override
            user.profile.save()

        set_country(user, request)
        return user, jwt_value


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):

    def pre_social_login(self, request, sociallogin):
        User = get_user_model()

        # TODO: make sure that the partnership is still in good standing or valid or whatever
        if sociallogin.user.pk:
            set_country(sociallogin.user, request)
            logger.info("setting connection to {}".format(sociallogin.user.profile.country))
            return
        try:
            # if user exists, connect the account to the existing account and login
            new_login_user = User.objects.get(email=sociallogin.user.email)
        except User.DoesNotExist:
            url = reverse('sociallogin_notamember', kwargs={'email': urlsafe_base64_encode(sociallogin.user.email)})
            raise ImmediateHttpResponse(HttpResponseRedirect(url))

        sociallogin.connect(request, new_login_user)
        set_country(new_login_user, request)
        perform_login(
            request,
            new_login_user,
            'none',
            redirect_url=sociallogin.get_redirect_url(request),
            signal_kwargs={"sociallogin": sociallogin}
        )


class CustomAccountAdapter(DefaultAccountAdapter):

    def is_open_for_signup(self, request):
        # quick way of disabling signups.
        return False

    def login(self, request, user):
        # if we need to add any other login validation, here would be the place.
        return super(CustomAccountAdapter, self).login(request, user)


class CsrfExemptSessionAuthentication(SessionAuthentication):

    def enforce_csrf(self, request):
        return


def custom_jwt_payload_handler(user):
    payload = jwt_payload_handler(user)
    payload['groups'] = list(user.groups.values_list('name', flat=True))
    return payload
