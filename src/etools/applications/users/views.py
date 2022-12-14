import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.transaction import atomic
from django.http import Http404, HttpResponseForbidden, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.generic import RedirectView
from django.views.generic.detail import DetailView

from rest_framework import mixins, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, GenericAPIView, ListAPIView, RetrieveAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from unicef_restlib.permissions import IsSuperUser

from etools.applications.organizations.models import Organization
from etools.applications.users.models import Country, Realm, UserProfile
from etools.applications.users.permissions import IsServiceNowUser
from etools.applications.users.serializers import (
    CountrySerializer,
    GroupSerializer,
    MinimalUserSerializer,
    ProfileRetrieveUpdateSerializer,
    SimpleProfileSerializer,
    SimpleUserSerializer,
    UserCreationSerializer,
    UserManagementSerializer,
)
from etools.libraries.azure_graph_api.tasks import retrieve_user_info

logger = logging.getLogger(__name__)


class ADUserAPIView(DetailView):
    template_name = 'admin/users/user/api.html'
    model = get_user_model()
    slug_field = slug_url_kwarg = 'username'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user and self.request.user.is_superuser:
            context['ad_dict'] = retrieve_user_info(self.object.username)
        return context


class ChangeUserRoleView(CreateAPIView, GenericAPIView):
    """
    Allows api user to change roles and workspaces for a specific user.
    """

    serializer_class = UserManagementSerializer
    permission_classes = [IsSuperUser | IsServiceNowUser]

    @atomic
    def create(self, request, *args, **kwargs):
        """
        Add a User Group
        :return: JSON
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.data
        details = {}

        try:
            user = get_object_or_404(get_user_model(), email=data['user_email'])
            try:
                workspace = get_object_or_404(Country, business_area_code=data['workspace'])
            except Country.MultipleObjectsReturned:
                return ValidationError("users in this business area need to be addressed via ticket due to multiple "
                                       "workspaces having the same business_area")
            roles = []
            for desired_role_name in data["roles"]:
                roles.append(get_object_or_404(Group, name=desired_role_name))
        except Http404 as e:
            raise ValidationError({"error": e})

        if not user.is_unicef_user():
            raise ValidationError({"error": "only users with UNICEF email addresses can be updated"})

        details["previous_roles"] = list(user.groups.all().values_list("name", flat=True))
        realms = []
        for role in roles:
            realms.append(Realm.objects.get_or_create(
                user=user,
                country=workspace,
                organization=user.profile.organization,
                group=role)[0])
        if data["access_type"] == "grant":
            # add unicef user role to roles list by default
            realms.append(Realm.objects.get_or_create(
                user=user,
                country=workspace,
                organization=user.profile.organization,
                group=Group.objects.get(name="UNICEF User"))[0])
            user.realms.add(*realms)
        elif data["access_type"] == "set":
            # add unicef user role to roles list by default
            realms.append(Realm.objects.get_or_create(
                user=user,
                country=workspace,
                organization=user.profile.organization,
                group=Group.objects.get(name="UNICEF User"))[0])
            user.realms_set.set(realms)
        else:
            user.realms\
                .filter(group__in=roles, country=workspace, organization=user.profile.organization)\
                .update(is_active=False)

        if user.profile.country_override and user.profile.country_override != workspace:
            user.profile.country_override = None
            details["country_override"] = "The user's country override has been removed"
        if user.profile.country != workspace:
            details["country"] = "The user has been moved from {} to {}".format(user.profile.country.name,
                                                                                workspace.name)
        user.profile.country = workspace
        user.profile.save()
        details["current_roles"] = list(user.groups.filter().values_list("name", flat=True))
        return JsonResponse({'email': user.email, "status": "success", "details": details},
                            content_type="application/json",
                            status=status.HTTP_200_OK)


class ChangeUserCountryView(APIView):
    """
    Allows a user to switch country context if they have access to more than one
    """

    ERROR_MESSAGES = {
        'country_does_not_exist': 'The Country that you are attempting to switch to does not exist',
        'access_to_country_denied': 'You do not have access to the country you are trying to switch to'
    }

    next_param = 'next'

    permission_classes = (IsAuthenticated, )

    def get_country_id(self):
        return self.request.data.get('country', None) or self.request.query_params.get('country', None)

    def get_country(self):
        country_id = self.get_country_id()

        try:
            country = Country.objects.get(id=country_id)
        except Country.DoesNotExist:
            raise DjangoValidationError(self.ERROR_MESSAGES['country_does_not_exist'], code='country_does_not_exist')

        return country

    def change_country(self):
        user = self.request.user
        country = self.get_country()

        if country == user.profile.country:
            return

        if country not in user.profile.countries_available.all():
            raise DjangoValidationError(self.ERROR_MESSAGES['access_to_country_denied'],
                                        code='access_to_country_denied')
        user.profile.country_override = country

        if user.profile.organization not in Organization.objects\
                .filter(realms__country=country, realms__user=user):
            user.profile.organization = None
        user.profile.save()

    def get_redirect_url(self):
        return self.request.GET.get(self.next_param, '/')

    def get(self, request, *args, **kwargs):
        try:
            self.change_country()
        except DjangoValidationError as err:
            return HttpResponseForbidden(str(err))

        return HttpResponseRedirect(self.get_redirect_url())

    def post(self, request, format=None):
        try:
            self.change_country()

        except DjangoValidationError as err:
            if err.code == 'access_to_country_denied':
                status_code = status.HTTP_403_FORBIDDEN
            else:
                status_code = status.HTTP_400_BAD_REQUEST
            return Response(str(err), status=status_code)

        return Response(status=status.HTTP_204_NO_CONTENT)


class StaffUsersView(ListAPIView):
    """
    Gets a list of Unicef Staff users in the current country.
    Country is determined by the currently logged in user.
    """
    model = UserProfile
    serializer_class = SimpleProfileSerializer
    permission_classes = (IsAdminUser, )

    def get_queryset(self):
        user = self.request.user
        user_ids = self.request.query_params.get("values", None)
        if user_ids:
            try:
                user_ids = [int(x) for x in user_ids.split(",")]
            except ValueError:
                raise ValidationError("Query parameter values are not integers")
            else:
                return self.model.objects.filter(
                    user__id__in=user_ids,
                    user__is_staff=True
                ).order_by('user__first_name')

        return self.model.objects.filter(
            country=user.profile.country,
            user__is_staff=True
        ).order_by('user__first_name')


class MyProfileAPIView(RetrieveUpdateAPIView):
    """
    Updates a UserProfile object
    """
    queryset = UserProfile.objects.all()
    serializer_class = ProfileRetrieveUpdateSerializer
    permission_classes = (IsAuthenticated, )

    def get_object(self):
        """
        Always returns current user's profile
        """
        try:
            obj = self.request.user.profile
        except AttributeError:
            self.request.user.save()
            obj = UserProfile.objects.get(user=self.request.user)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)
        return obj


class UsersDetailAPIView(RetrieveAPIView):
    """
    Retrieve a User in the current country
    """
    queryset = UserProfile.objects.all()
    serializer_class = SimpleProfileSerializer
    permission_classes = (IsAuthenticated, )

    def retrieve(self, request, pk=None):
        """
        Returns a UserProfile object for this PK
        """
        try:
            queryset = self.queryset.get(user__id=pk)
        except UserProfile.DoesNotExist:
            data = {}
        else:
            serializer = self.serializer_class(queryset)
            data = serializer.data
        return Response(
            data,
            status=status.HTTP_200_OK
        )


class GroupViewSet(mixins.RetrieveModelMixin,
                   mixins.ListModelMixin,
                   mixins.CreateModelMixin,
                   viewsets.GenericViewSet):
    """
    Returns a list of all User Groups
    """
    queryset = Group.objects.order_by('name')  # Provide consistent ordering
    serializer_class = GroupSerializer
    permission_classes = (IsAdminUser,)

    def create(self, request, *args, **kwargs):
        """
        Add a User Group
        :return: JSON
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.instance = serializer.save()
        data = serializer.data

        try:
            permissions = request.data['permissions']
            for perm in permissions:
                serializer.instance.permissions.add(perm)
            serializer.save()
        except Exception:
            pass

        headers = self.get_success_headers(serializer.data)
        return Response(data, status=status.HTTP_201_CREATED,
                        headers=headers)


class UserViewSet(mixins.RetrieveModelMixin,
                  mixins.ListModelMixin,
                  viewsets.GenericViewSet):
    """
    Returns a list of all Users
    """
    queryset = get_user_model().objects.all()
    serializer_class = UserCreationSerializer
    permission_classes = (IsAdminUser,)

    def get_queryset(self):
        # we should only return workspace users.
        queryset = super().get_queryset()
        queryset = queryset.prefetch_related('profile', 'realms', 'user_permissions')
        # Filter for Partnership Managers only
        driver_qps = self.request.query_params.get("drivers", "")
        if driver_qps.lower() == "true":
            queryset = queryset.filter(realms__group__name='Driver')

        filter_param = self.request.query_params.get("partnership_managers", "")
        if filter_param.lower() == "true":
            queryset = queryset.filter(realms__group__name="Partnership Manager")

        if "values" in self.request.query_params.keys():
            # Used for ghost data - filter in all(), and return straight away.
            try:
                ids = [int(x) for x in self.request.query_params.get("values").split(",")]
            except ValueError:
                raise ValidationError("ID values must be integers")
            else:
                queryset = queryset.filter(id__in=ids)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.filter(realms__group__name="UNICEF User")
        filter_param = self.request.query_params.get("all", "")
        if filter_param.lower() != "true":
            queryset = queryset.filter(profile__country=self.request.user.profile.country)

        def get_serializer(*args, **kwargs):
            if request.GET.get('verbosity') == 'minimal':
                serializer_cls = MinimalUserSerializer
            else:
                serializer_cls = SimpleUserSerializer

            return serializer_cls(*args, **kwargs)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = get_serializer(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        serializer = get_serializer(queryset, many=True, context=self.get_serializer_context())
        return Response(serializer.data)


class CountriesViewSet(ListAPIView):
    """
    Gets the list of countries
    """
    model = Country
    serializer_class = CountrySerializer

    def get_queryset(self):
        return Country.objects.all()


class ModuleRedirectView(RedirectView):
    url = '/menu/'
    permanent = False

    # def get_redirect_url(self, *args, **kwargs):
    #     if not self.request.user.is_staff:
    #         if ThirdPartyMonitor.as_group() in self.request.user.groups.all():
    #             return '/tpm/'
    #
    #         elif Auditor.as_group() in self.request.user.groups.all():
    #             if Engagement.objects.filter(
    #                     status__in=[Engagement.PARTNER_CONTACTED, Engagement.REPORT_SUBMITTED],
    #                     staff_members__user=self.request.user,
    #             ):
    #                 return '/ap/'
    #             elif Assessment.objects.filter(
    #                     Q(partner__psea_assessment__assessor__user=self.request.user) |
    #                     Q(partner__psea_assessment__assessor__auditor_firm_staff__user=self.request.user),
    #                     status__in=[
    #                         Assessment.STATUS_DRAFT,
    #                         Assessment.STATUS_ASSIGNED,
    #                         Assessment.STATUS_IN_PROGRESS,
    #                         Assessment.STATUS_SUBMITTED,
    #                         Assessment.STATUS_REJECTED,
    #                     ],
    #             ):
    #                 return '/psea/'
    #             elif Engagement.objects.filter(
    #                     agreement__auditor_firm__staff_members__user=self.request.user,
    #             ):
    #                 return '/ap/'
    #             else:
    #                 return '/psea/'
    #
    #     return super().get_redirect_url(*args, **kwargs)
