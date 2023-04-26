import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect

from rest_framework.authentication import (
    BasicAuthentication,
    get_authorization_header,
    SessionAuthentication,
    TokenAuthentication,
)
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication
from social_core.backends.azuread_b2c import AzureADB2COAuth2
from social_core.exceptions import AuthCanceled, AuthMissingParameter
from social_core.pipeline import social_auth, user as social_core_user
from social_django.middleware import SocialAuthExceptionMiddleware

from etools.applications.organizations.models import Organization
from etools.applications.users.models import Country, Realm
from etools.libraries.tenant_support.utils import set_country

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


def user_details(strategy, details, backend, user=None, *args, **kwargs):
    # This is where we update the user
    # see what the property to map by is here
    if user:
        business_area_code = details.get("business_area_code", 'defaultBA1235')

        try:
            country = Country.objects.get(business_area_code=business_area_code)
        except Country.DoesNotExist:
            country = Country.objects.get(name='UAT')

        if details.get("idp") == "UNICEF Azure AD":
            unicef_org = Organization.objects.get(name='UNICEF')
            user_has_unicef_group = user.realms.filter(country=user.profile.country or country,
                                                       organization=unicef_org,
                                                       is_active=True,
                                                       group=Group.objects.get(name='UNICEF User')).exists()
            if not user_has_unicef_group:
                Realm.objects.update_or_create(
                    user=user,
                    country=user.profile.country or country,
                    organization=unicef_org,
                    group=Group.objects.get(name='UNICEF User'),
                    active=False, defaults={"active": True}
                )
                user.is_staff = True
                user.save(update_fields=['is_staff'])
                user.profile.organization = unicef_org
                user.profile.save(update_fields=['organization'])

        if not user.profile.country:
            user.profile.country = country
            user.profile.save(update_fields=['country'])
        # TODO: Hotfix. details not providing business area code
        # elif not user.profile.country_override:
        #     # make sure that we update the workspace based business area
        #     if business_area_code != user.profile.country.business_area_code:
        #         user.profile.country = country
        #         user.profile.save()

    return social_core_user.user_details(strategy, details, backend, user, *args, **kwargs)


class CustomAzureADBBCOAuth2(AzureADB2COAuth2):
    BASE_URL = 'https://{tenant_id}.b2clogin.com/{tenant_id}.onmicrosoft.com'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.redirect_uri = settings.HOST + '/social/complete/azuread-b2c-oauth2/'


class CustomSocialAuthExceptionMiddleware(SocialAuthExceptionMiddleware):

    def process_exception(self, request, exception):
        if isinstance(exception, (AuthCanceled, AuthMissingParameter)):
            return HttpResponseRedirect(self.get_redirect_uri(request, exception))
        else:
            raise exception

    def get_redirect_uri(self, request, exception):
        error = request.GET.get('error', None)

        # This is what we should expect:
        # ['AADB2C90118: The user has forgotten their password.\r\n
        # Correlation ID: 7e8c3cf9-2fa7-47c7-8924-a1ea91137ba9\r\n
        # Timestamp: 2018-11-13 11:37:56Z\r\n']
        error_description = request.GET.get('error_description', None)

        if error == "access_denied" and error_description is not None:
            if 'AADB2C90118' in error_description:
                auth_class = CustomAzureADBBCOAuth2()
                redirect_home = auth_class.get_redirect_uri()
                redirect_url = auth_class.base_url + '/oauth2/v2.0/' + \
                    'authorize?p=' + settings.SOCIAL_PASSWORD_RESET_POLICY + \
                    '&client_id=' + settings.KEY + \
                    '&nonce=defaultNonce&redirect_uri=' + redirect_home + \
                    '&scope=openid+email&response_type=code'

                return redirect_url

        # TODO: In case of password reset the state can't be verified figure out a way to log the user in after reset
        return settings.LOGIN_URL


class DRFBasicAuthMixin(BasicAuthentication):
    def authenticate(self, request):
        super_return = super().authenticate(request)
        if not super_return:
            return None

        user, token = super_return
        set_country(user, request)
        return user, token


class eToolsOLCTokenAuth(TokenAuthentication):
    def authenticate(self, request):
        key = get_authorization_header(request)
        try:
            token = key.decode()
        except UnicodeError:
            # 'Invalid token header. '
            # 'Token string should not contain invalid characters.'
            return None
        if bool(token == f"Token {settings.ETOOLS_OFFLINE_TOKEN}"):
            try:
                email = request.data.get("user")
                user = get_user_model().objects.get(email=email)
            except get_user_model().DoesNotExist:
                return None
            else:
                set_country(user, request)
                return user, token
        return None


class EtoolsTokenAuthentication(TokenAuthentication):

    def authenticate(self, request):
        super_return = super().authenticate(request)
        if not super_return:
            return None

        user, token = super_return
        set_country(user, request)
        return user, token


class EToolsTenantJWTAuthentication(JWTAuthentication):
    """
    Handles setting the tenant after a JWT successful authentication
    """

    def authenticate(self, request):

        authentication = super().authenticate(request)
        if authentication is None:
            return
        user, validated_token = authentication

        if not user.profile.country:
            raise PermissionDenied(detail='No country found for user')

        if user.profile.country_override and user.profile.country != user.profile.country_override:
            user.profile.country = user.profile.country_override
            user.profile.save()

        set_country(user, request)
        return user, validated_token


class CsrfExemptSessionAuthentication(SessionAuthentication):

    def enforce_csrf(self, request):
        return
