import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from rest_framework.authentication import (
    BasicAuthentication,
    get_authorization_header,
    SessionAuthentication,
    TokenAuthentication,
)
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication
from social_core.pipeline import user as social_core_user

from etools.applications.users.models import Country
from etools.libraries.tenant_support.utils import set_country

logger = logging.getLogger(__name__)


def user_details(strategy, details, backend, user=None, *args, **kwargs):
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
        # TODO: Hotfix. details not providing business area code
        # elif not user.profile.country_override:
        #     # make sure that we update the workspace based business area
        #     if business_area_code != user.profile.country.business_area_code:
        #         user.profile.country = country
        #         user.profile.save()

    return social_core_user.user_details(strategy, details, backend, user, *args, **kwargs)


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
