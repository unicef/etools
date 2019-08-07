import logging

from rest_framework.generics import ListAPIView

from etools.applications.users import views as v1
from etools.applications.users.models import Country
from etools.applications.users.serializers import CountrySerializer
from etools.libraries.pythonlib.warnings import DeprecatedAPIClass

logger = logging.getLogger(__name__)


class ChangeUserCountryView(DeprecatedAPIClass, v1.ChangeUserCountryView):
    """Stub for ChangeUserCountryView"""


class StaffUsersView(DeprecatedAPIClass, v1.StaffUsersView):
    """Stub for StaffUsersView"""


class CountryView(DeprecatedAPIClass, ListAPIView):
    """
    Gets a list of Unicef Staff users in the current country.
    Country is determined by the currently logged in user.
    """
    model = Country
    serializer_class = CountrySerializer

    def get_queryset(self):
        user = self.request.user
        if not user.profile.country:
            logger.warning('{} has not an assigned country'.format(user))
            return self.model.objects.none()
        return self.model.objects.filter(
            name=user.profile.country.name,
        )


class MyProfileAPIView(DeprecatedAPIClass, v1.MyProfileAPIView):
    """stub for MyProfileAPIView"""


class UsersDetailAPIView(DeprecatedAPIClass, v1.UsersDetailAPIView):
    """Stub for UsersDetailAPIView"""


class GroupViewSet(DeprecatedAPIClass, v1.GroupViewSet):
    """Stub for GroupViewSet"""


class UserViewSet(DeprecatedAPIClass, v1.UserViewSet):
    """Stub for UserViewSet"""


class OfficeViewSet(DeprecatedAPIClass, v1.OfficeViewSet):
    """Stub for OfficeViewSet"""


class ModuleRedirectView(DeprecatedAPIClass, v1.ModuleRedirectView):
    """Stub for ModuleRedirectView"""


class CountriesViewSet(DeprecatedAPIClass, ListAPIView):
    """
    Gets the list of countries
    """
    model = Country
    serializer_class = CountrySerializer

    def get_queryset(self):
        return Country.objects.prefetch_related('local_currency').all()
