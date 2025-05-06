from django.contrib.auth import get_user_model
from django.db import connection
from django.db.models import Value
from django.db.models.functions import Concat
from django.http import Http404
from django.utils.functional import cached_property

from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from unicef_attachments.models import FileType as AttachmentFileType
from unicef_locations.models import GatewayType

from etools.applications.attachments.models import AttachmentFlat
from etools.applications.funds.models import FundsReservationItem
from etools.applications.governments.models import GDDAmendment, GDDRisk
from etools.applications.organizations.models import Organization
from etools.applications.partners.models import (
    Agreement,
    AgreementAmendment,
    Assessment,
    FileType,
    Intervention,
    InterventionAmendment,
    InterventionReview,
    InterventionRisk,
    InterventionSupplyItem,
    OrganizationType,
    PartnerOrganization,
)
from etools.applications.partners.permissions import UserIsPartnerStaffMemberPermission
from etools.applications.partners.views.v2 import choices_to_json_ready
from etools.applications.reports.models import CountryProgramme, Result, ResultType
from etools.libraries.djangolib.fields import CURRENCIES


class PMPBaseViewMixin:
    # TODO need to set correct permissions
    # see ch21937
    permission_classes = [IsAuthenticated]

    def is_partner_staff(self):
        """
        Flag indicator shows whether authenticated user is a partner staff
        based on profile organization relationship_type
        """
        is_staff = self.request.user.is_authenticated and self.request.user.profile.organization and \
            'partner' in self.request.user.profile.organization.relationship_types
        if not is_staff and not self.request.user.is_unicef_user():
            raise PermissionDenied()

        return is_staff

    def current_partner(self):
        """List of partners the user is associated with"""
        if not self.is_partner_staff():
            return None
        return PartnerOrganization.objects.filter(
            organization=self.request.user.profile.organization,
            organization__realms__user=self.request.user,
            organization__realms__is_active=True,
        ).first()

    def get_pd(self, pd_pk):
        try:
            if not self.is_partner_staff():
                return Intervention.objects.detail_qs().get(pk=pd_pk)
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


class PMPDropdownsListApiView(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser | UserIsPartnerStaffMemberPermission)

    @cached_property
    def partner(self):
        return PartnerOrganization.objects.filter(
            organization=self.request.user.profile.organization,
            organization__realms__country=connection.tenant,
            organization__realms__user=self.request.user).first()

    def get_signed_by_unicef_users(self, request) -> list:
        return list(get_user_model().objects.filter(
            realms__group__name__in=['Senior Management Team'],
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
        data = FileType.objects.filter(name__in=[i[0] for i in FileType.NAME_CHOICES]).values('id', 'name')
        # order items according to their presence in choices list
        display_name_choices = list(dict(FileType.NAME_CHOICES).keys())
        sorted_data = list(sorted(data, key=lambda x: display_name_choices.index(x['name'])))
        for d in sorted_data:
            d['name'] = FileType.NAME_CHOICES[d['name']]
        return sorted_data

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

    def get_cso_types(self):
        cso_types = Organization.objects.values_list(
            'cso_type',
            flat=True,
        ).exclude(
            cso_type__isnull=True,
        ).exclude(
            cso_type__exact='',
        ).order_by('cso_type').distinct('cso_type')
        return choices_to_json_ready([(ct, Organization.CSO_TYPES[ct]) for ct in cso_types])

    def get_local_currency(self):
        local_workspace = self.request.user.profile.country
        if local_workspace.local_currency:
            return local_workspace.local_currency.pk
        return None

    def get(self, request):
        """
        Return All dropdown values used for Agreements form
        """
        response_data = {
            'cp_outputs': self.get_cp_outputs(request),
            'file_types': self.get_file_types(request),
            'cso_types': self.get_cso_types(),
            'partner_types': choices_to_json_ready(OrganizationType.CHOICES),
            'agency_choices': choices_to_json_ready(
                PartnerOrganization.AGENCY_CHOICES,
            ),
            'partner_risk_rating': choices_to_json_ready(
                PartnerOrganization.RISK_RATINGS,
            ),
            'assessment_types': choices_to_json_ready(
                Assessment.ASSESSMENT_TYPES,
            ),
            'agreement_types': choices_to_json_ready(
                Agreement.AGREEMENT_TYPES,
            ),
            'agreement_status': choices_to_json_ready(
                Agreement.STATUS_CHOICES,
                sort_choices=False,
            ),
            'agreement_amendment_types': choices_to_json_ready(
                AgreementAmendment.AMENDMENT_TYPES,
            ),
            'intervention_doc_type': choices_to_json_ready(
                Intervention.INTERVENTION_TYPES,
            ),
            'intervention_status': choices_to_json_ready(
                Intervention.INTERVENTION_STATUS,
                sort_choices=False,
            ),
            'intervention_amendment_types': choices_to_json_ready(
                InterventionAmendment.AMENDMENT_TYPES,
            ),
            'gdd_amendment_types': choices_to_json_ready(
                GDDAmendment.AMENDMENT_TYPES,
            ),
            'gpd_statuses': choices_to_json_ready(
                Intervention.INTERVENTION_STATUS,
                sort_choices=False,
            ),
            'currencies': choices_to_json_ready(CURRENCIES),
            'local_currency': self.get_local_currency(),
            'location_types': GatewayType.objects.values(
                'id',
                'name',
                'admin_level',
            ).order_by('id'),
            'attachment_types': AttachmentFileType.objects.values_list(
                "label",
                flat=True,
            ),
            'attachment_types_active': AttachmentFlat.get_file_types(),
            'partner_file_types': FileType.objects.values_list(
                "name",
                flat=True,
            ),
            'sea_risk_ratings': choices_to_json_ready(
                PartnerOrganization.RISK_RATINGS,
            ),
            'gender_equity_sustainability_ratings': choices_to_json_ready(
                Intervention.RATING_CHOICES,
                sort_choices=False,
            ),
            'risk_types': choices_to_json_ready(
                InterventionRisk.RISK_TYPE_CHOICES,
                sort_choices=False,
            ),
            'gpd_risk_types': choices_to_json_ready(
                GDDRisk.RISK_TYPE_CHOICES,
                sort_choices=False),
            'cash_transfer_modalities': choices_to_json_ready(
                Intervention.CASH_TRANSFER_CHOICES,
                sort_choices=False,
            ),
            'review_types': choices_to_json_ready(
                InterventionReview.ALL_REVIEW_TYPES,
                sort_choices=False,
            ),
            'supply_item_provided_by': choices_to_json_ready(
                InterventionSupplyItem.PROVIDED_BY_CHOICES,
                sort_choices=False,
            ),
        }
        if request.user.is_staff:
            response_data.update({
                'signed_by_unicef_users': self.get_signed_by_unicef_users(request),
                'country_programmes': self.get_country_programmes(request),
                'donors': self.get_donors(request),
                'grants': self.get_grants(request),
            })

        return Response(response_data, status=status.HTTP_200_OK)
