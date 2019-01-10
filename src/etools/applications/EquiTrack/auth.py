import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

import jwt
from rest_framework.authentication import BasicAuthentication, SessionAuthentication, TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework_jwt.settings import api_settings
from rest_framework_jwt.utils import jwt_payload_handler
from social_core.pipeline import social_auth
from social_core.pipeline import user as social_core_user
from social_core.backends.azuread_b2c import AzureADB2COAuth2

from etools.applications.EquiTrack.utils import set_country
from etools.applications.users.models import Country

jwt_decode_handler = api_settings.JWT_DECODE_HANDLER
logger = logging.getLogger(__name__)


def social_details(backend, details, response, *args, **kwargs):
    r = social_auth.social_details(backend, details, response, *args, **kwargs)
    r['details']['idp'] = response.get('idp')

    if not r['details'].get('email'):
        if not response.get('email'):
            r['details']['email'] = response["signInNames.emailAddress"]
        else:
            r['details']['email'] = response.get('email')

    email = r['details'].get('email')
    if isinstance(email, str):
        r['details']['email'] = email.lower()
    return r


def get_username(strategy, details, backend, user=None, *args, **kwargs):
    return {'username': details.get('email')}


def create_user(strategy, details, backend, user=None, *args, **kwargs):
    """ Overwrite social_account.user.create_user to only create new users if they're UNICEF"""

    if user:
        return {'is_new': False}

    fields = dict((name, kwargs.get(name, details.get(name)))
                  for name in backend.setting('USER_FIELDS', social_core_user.USER_FIELDS))
    if not fields:
        return

    response = kwargs.get('response')
    if response:
        email = response.get('email') or response.get("signInNames.emailAddress")
        if not email.endswith("unicef.org"):
            return
    return {
        'is_new': True,
        'user': strategy.create_user(**fields)
    }


def user_details(strategy, details, user=None, *args, **kwargs):
    # This is where we update the user
    # see what the property to map by is here
    if user:
        user_groups = [group.name for group in user.groups.all()]
        business_area_code = details.get("business_area_code", 'defaultBA1235')

        try:
            country = Country.objects.get(business_area_code=business_area_code)
        except Country.DoesNotExist:
            country = Country.objects.get(name='UAT')

        if details.get("idp") == "UNICEF Azure AD" and "UNICEF User" not in user_groups:
            user.groups.add(Group.objects.get(name='UNICEF User'))
            user.is_staff = True
            user.save()

        if not user.profile.country:
            user.profile.country = country
            user.profile.save()
        elif not user.profile.country_override:
            # make sure that we update the workspace based business area
            if business_area_code != user.profile.country.business_area_code:
                user.profile.country = country
                user.profile.save()

    return social_core_user.user_details(strategy, details, user, *args, **kwargs)


class CustomAzureADBBCOAuth2(AzureADB2COAuth2):
    def __init__(self, *args, **kwargs):
        super(CustomAzureADBBCOAuth2, self).__init__(*args, **kwargs)
        self.redirect_uri = 'http://localhost:8082/social/complete/azuread-b2c-oauth2/'


class DRFBasicAuthMixin(BasicAuthentication):
    def authenticate(self, request):
        super_return = super().authenticate(request)
        if not super_return:
            return None

        user, token = super_return
        set_country(user, request)
        return user, token


class EtoolsTokenAuthentication(TokenAuthentication):

    def authenticate(self, request):
        super_return = super().authenticate(request)
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
            user, jwt_value = super().authenticate(request)
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


class CsrfExemptSessionAuthentication(SessionAuthentication):

    def enforce_csrf(self, request):
        return


def custom_jwt_payload_handler(user):
    payload = jwt_payload_handler(user)
    payload['groups'] = list(user.groups.values_list('name', flat=True))
    return payload
