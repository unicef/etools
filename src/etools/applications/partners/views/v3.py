from django.contrib.auth import get_user_model
from django.db.models import Value
from django.db.models.functions import Concat
from django.http import Http404
from django.utils.functional import cached_property

from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from etools.applications.funds.models import FundsReservationItem
from etools.applications.partners.models import FileType, Intervention, PartnerOrganization, PartnerStaffMember
from etools.applications.partners.permissions import UserIsPartnerStaffMemberPermission
from etools.applications.partners.views.v2 import choices_to_json_ready
from etools.applications.reports.models import CountryProgramme, Result, ResultType


class PMPBaseViewMixin:
    # TODO need to set correct permissions
    # see ch21937
    permission_classes = [IsAuthenticated]

    def is_partner_staff(self):
        """Flag indicator whether user is a partner"""
        return self.request.user.is_authenticated and bool(PartnerStaffMember.get_for_user(self.request.user))

    def partners(self):
        """List of partners user associated with"""
        if not self.is_partner_staff():
            return []
        return PartnerOrganization.objects.filter(
            staff_members__email=self.request.user.email,
        )

    def get_pd(self, pd_pk):
        try:
            if not self.is_partner_staff():
                return Intervention.objects.get(pk=pd_pk)
            return self.pds().get(pk=pd_pk)
        except Intervention.DoesNotExist:
            return None

    def get_pd_or_404(self, pd_pk):
        pd = self.get_pd(pd_pk)
        if pd is None:
            raise Http404
        return pd

    def pds(self):
        """List of PDs user associated with"""
        if not self.is_partner_staff():
            return []
        return Intervention.objects.filter(
            partner_focal_points__email=self.request.user.email,
        )

    def offices(self):
        """List of Offices user associated with"""
        if not self.is_partner_staff():
            return []
        return Intervention.objects.filter(
            partner_focal_points__email=self.request.user.email,
        )

    def map_serializer(self, serializer):
        default_serializer, partner_serializer = self.SERIALIZER_OPTIONS.get(
            serializer,
            (None, None),
        )
        if self.is_partner_staff():
            return partner_serializer
        return default_serializer


class PMPDropdownsListApiView(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser | UserIsPartnerStaffMemberPermission)

    @cached_property
    def partner(self):
        return PartnerOrganization.objects.filter(staff_members__email=self.request.user.email).first()

    def get_signed_by_unicef_users(self, request) -> list:
        return list(get_user_model().objects.filter(
            groups__name__in=['Senior Management Team'],
            profile__country=request.user.profile.country
        ).annotate(
            name=Concat('first_name', Value(' '), 'last_name')
        ).values('id', 'name', 'username', 'email'))

    def get_country_programmes(self, request) -> list:
        return list(CountryProgramme.objects.all_active_and_future.values('id', 'wbs', 'name', 'from_date', 'to_date'))

    def get_cp_outputs(self, request) -> list:
        results = Result.objects.filter(result_type__name=ResultType.OUTPUT, wbs__isnull=False)
        if not request.user.is_staff:
            results = results.filter(intervention_links__intervention__agreement__partner=self.partner)

        return [
            {"id": r.id, "name": r.output_name, "wbs": r.wbs, "country_programme": r.country_programme.id}
            for r in results
        ]

    def get_file_types(self, request) -> list:
        return list(FileType.objects.filter(name__in=[i[0] for i in FileType.NAME_CHOICES]).all().values())

    def get_donors(self, request) -> list:
        return choices_to_json_ready(
            list(FundsReservationItem.objects.filter(
                donor__isnull=False
            ).order_by('donor').values_list('donor', flat=True).distinct('donor')),
            sort_choices=False
        )

    def get_grants(self, request) -> list:
        return choices_to_json_ready(
            list(FundsReservationItem.objects.filter(
                donor__isnull=False
            ).order_by('grant_number').values_list('grant_number', flat=True).distinct('grant_number')),
            sort_choices=False
        )

    def get(self, request):
        """
        Return All dropdown values used for Agreements form
        """
        response_data = {
            'cp_outputs': self.get_cp_outputs(request),
            'file_types': self.get_file_types(request),
        }
        if request.user.is_staff:
            response_data.update({
                'signed_by_unicef_users': self.get_signed_by_unicef_users(request),
                'country_programmes': self.get_country_programmes(request),
                'donors': self.get_donors(request),
                'grants': self.get_grants(request),
            })

        return Response(response_data, status=status.HTTP_200_OK)
