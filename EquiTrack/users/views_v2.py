import logging

from rest_framework.generics import ListAPIView

from users import views as v1
from users.models import Country
from users.serializers import CountrySerializer

logger = logging.getLogger(__name__)


class UserAuthAPIView(v1.UserAuthAPIView):
    """Stub for UserAuthAPIView"""


class ChangeUserCountryView(v1.ChangeUserCountryView):
    """Stub for ChangeUserCountryView"""


class StaffUsersView(v1.StaffUsersView):
    """Stub for StaffUsersView"""


class CountryView(ListAPIView):
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


class MyProfileAPIView(v1.MyProfileAPIView):
    """stub for MyProfileAPIView"""


class UsersDetailAPIView(v1.UsersDetailAPIView):
    """Stub for UsersDetailAPIView"""


class ProfileEdit(v1.ProfileEdit):
    """Stub for ProfileEdit"""


class GroupViewSet(v1.GroupViewSet):
    """Stub for GroupViewSet"""


class UserViewSet(v1.UserViewSet):
    """Stub for UserViewSet"""


class OfficeViewSet(v1.OfficeViewSet):
    """Stub for OfficeViewSet"""


class SectionViewSet(v1.SectionViewSet):
    """Stub for SectionViewSet"""


class ModuleRedirectView(v1.ModuleRedirectView):
    """Stub for ModuleRedirectView"""
