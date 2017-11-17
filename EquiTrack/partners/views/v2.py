import datetime
import operator

from django.contrib.auth import models
from django.db.models.functions import Concat
from django.db.models import F, Value
from model_utils import Choices

from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAdminUser
from rest_framework.views import APIView

from publics.models import Currency

from reports.models import (
    CountryProgramme,
    Result,
    ResultType,
)
from funds.models import Donor
from locations.models import GatewayType

from partners.models import (
    PartnerOrganization,
    Agreement,
    PartnerStaffMember,
    PartnerType,
    Assessment,
    InterventionAmendment,
    Intervention,
    FileType,
    AgreementAmendment,
)
from partners.serializers.partner_organization_v2 import (
    PartnerStaffMemberDetailSerializer,
    PartnerStaffMemberCreateUpdateSerializer,
)
from partners.permissions import PartnershipManagerPermission
from partners.filters import PartnerScopeFilter


class PartnerStaffMemberDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = PartnerStaffMember.objects.all()
    serializer_class = PartnerStaffMemberDetailSerializer
    permission_classes = (PartnershipManagerPermission,)
    filter_backends = (PartnerScopeFilter,)

    def get_serializer_class(self, format=None):
        if self.request.method in ["PUT", "PATCH"]:
            return PartnerStaffMemberCreateUpdateSerializer
        return super(PartnerStaffMemberDetailAPIView, self).get_serializer_class()


def choices_to_json_ready(choices):
    if isinstance(choices, dict):
        choice_list = [(k, v) for k, v in choices.items()]
    elif isinstance(choices, Choices):
        choice_list = [(k, v) for k, v in choices]
    elif isinstance(choices, list):
        choice_list = []
        for c in choices:
            if isinstance(c, tuple):
                choice_list.append((c[0], c[1]))
            else:
                choice_list.append((c, c))
    else:
        choice_list = choices

    return [{'label': choice[1], 'value': choice[0]} for choice in choice_list]


class PMPStaticDropdownsListAPIView(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request):
        """
        Return All Static values used for dropdowns in the frontend
        """

        local_workspace = self.request.user.profile.country
        cso_types = PartnerOrganization.objects.values_list('cso_type', flat=True)
        cso_types = cso_types.exclude(cso_type__isnull=True).exclude(cso_type__exact='')
        cso_types = cso_types.order_by('cso_type').distinct('cso_type')
        cso_types = choices_to_json_ready(list(cso_types))
        partner_types = choices_to_json_ready(PartnerType.CHOICES)
        agency_choices = choices_to_json_ready(PartnerOrganization.AGENCY_CHOICES)
        assessment_types = choices_to_json_ready(Assessment.ASSESSMENT_TYPES)
        agreement_types = choices_to_json_ready(Agreement.AGREEMENT_TYPES)
        agreement_status = choices_to_json_ready(Agreement.STATUS_CHOICES)
        agreement_amendment_types = choices_to_json_ready(AgreementAmendment.AMENDMENT_TYPES)
        intervention_doc_type = choices_to_json_ready(Intervention.INTERVENTION_TYPES)
        intervention_status = choices_to_json_ready(Intervention.INTERVENTION_STATUS)
        intervention_amendment_types = choices_to_json_ready(InterventionAmendment.AMENDMENT_TYPES)
        location_types = GatewayType.objects.values('id', 'name', 'admin_level').order_by('id')
        currencies = choices_to_json_ready(Currency.objects.values_list('id', 'code').order_by('code').distinct())

        local_currency = local_workspace.local_currency.id if local_workspace.local_currency else None

        return Response(
            {
                'cso_types': cso_types,
                'partner_types': partner_types,
                'agency_choices': agency_choices,
                'assessment_types': assessment_types,
                'agreement_types': agreement_types,
                'agreement_status': agreement_status,
                'agreement_amendment_types': agreement_amendment_types,
                'intervention_doc_type': intervention_doc_type,
                'intervention_status': intervention_status,
                'intervention_amendment_types': intervention_amendment_types,
                'currencies': currencies,
                'local_currency': local_currency,
                'location_types': location_types
            },
            status=status.HTTP_200_OK
        )


class PMPDropdownsListApiView(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request):
        """
        Return All dropdown values used for Agreements form
        """
        signed_by_unicef = list(models.User.objects.filter(
            groups__name__in=['Senior Management Team'],
            profile__country=request.tenant).annotate(
                full_name=Concat('first_name', Value(' '), 'last_name'), user_id=F('id')
        ).values('user_id', 'full_name', 'username', 'email'))

        country_programmes = list(CountryProgramme.objects.all_active_and_future.values('id', 'wbs', 'name',
                                                                                        'from_date', 'to_date'))
        cp_outputs = [{"id": r.id, "name": r.output_name, "wbs": r.wbs, "country_programme": r.country_programme.id}
                      for r in Result.objects.filter(result_type__name=ResultType.OUTPUT, wbs__isnull=False)]
        file_types = list(FileType.objects.filter(name__in=[i[0] for i in FileType.NAME_CHOICES])
                          .all().values())
        donors = list(Donor.objects.all().values())

        return Response(
            {
                'signed_by_unicef_users': signed_by_unicef,
                'country_programmes': country_programmes,
                'cp_outputs': cp_outputs,
                'file_types': file_types,
                'donors': donors,

            },
            status=status.HTTP_200_OK
        )


class PartnershipDashboardAPIView(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request, ct_pk=None, office_pk=None):
        """
        Return the aggregation data for Intervention
        """

        current = datetime.date.today()
        last_year = datetime.date(current.year - 1, 12, 31)

        # Use given CountryProgramme pk to filter Intervention
        if ct_pk:
            interventions = Intervention.objects.detail_qs().filter(agreement__country_programme=ct_pk)

        # Otherwise, use current CountryProgramme this year to filter Intervention
        else:
            currentCountryProgramme = CountryProgramme.main_active()

            interventions = Intervention.objects.detail_qs().filter(
                agreement__country_programme=currentCountryProgramme)

        # If Office pk is given, filter even more
        if office_pk:
            interventions = interventions.filter(offices=office_pk)

        # Categorize active Interventions
        active_partnerships = interventions.filter(
            status=Intervention.ACTIVE,
            start__isnull=False,
            end__isnull=False
        )
        total_this_year = interventions.filter(start__year=current.year)
        active_this_year = active_partnerships.filter(start__year=current.year)
        total_last_year = interventions.filter(end__lte=last_year, end__year=last_year.year)
        active_last_year = active_partnerships.filter(end__lte=last_year, end__year=last_year.year)
        total_expire_in_two_months = interventions.filter(
            end__range=[current, current + datetime.timedelta(days=60)])
        expire_in_two_months = active_partnerships.filter(
            end__range=[current, current + datetime.timedelta(days=60)])

        def total_value_for_parternships(partnerships):
            sum_cash = sum(
                map(lambda pd: pd.total_unicef_cash, partnerships))
            return sum_cash

        result = {'partners': {}}

        # Count active Interventions by its type
        for p_type in [
            PartnerType.BILATERAL_MULTILATERAL,
            PartnerType.CIVIL_SOCIETY_ORGANIZATION,
            PartnerType.UN_AGENCY,
        ]:
            result['partners'][p_type] = active_partnerships.filter(
                agreement__partner__partner_type=p_type).count()

        # Count GovernmentInterventions separately
        result['partners'][PartnerType.GOVERNMENT] = 0

        # (1) Number and value of Active Interventions for this year
        result['active_count'] = len(active_partnerships)
        result['total_count'] = len(interventions)
        result['active_value'] = total_value_for_parternships(active_partnerships)
        result['active_percentage'] = "{0:.0f}%".format(
            operator.truediv(result['active_count'], result['total_count']) * 100) \
            if result['total_count'] and result['active_count'] else "0%"

        # (2a) Number and value of Approved Interventions this year
        result['total_this_year_count'] = len(total_this_year)
        result['active_this_year_count'] = len(active_this_year)
        result['active_this_year_value'] = total_value_for_parternships(active_this_year)
        result['active_this_year_percentage'] = "{0:.0f}%".format(
            operator.truediv(result['active_this_year_count'], result['total_this_year_count']) * 100) \
            if result['total_this_year_count'] and result['active_this_year_count'] else "0%"

        # (2b) Number and value of Approved Interventions last year
        result['total_last_year_count'] = len(total_last_year)
        result['active_last_year_count'] = len(active_last_year)
        result['active_last_year_value'] = total_value_for_parternships(active_last_year)
        result['active_last_year_percentage'] = "{0:.0f}%".format(
            operator.truediv(result['active_last_year_count'], result['total_last_year_count']) * 100) \
            if result['total_last_year_count'] and result['active_last_year_count'] else "0%"

        # (3) Number and Value of Expiring Interventions in next two months
        result['total_expire_in_two_months_count'] = len(total_expire_in_two_months)
        result['expire_in_two_months_count'] = len(expire_in_two_months)
        result['expire_in_two_months_value'] = total_value_for_parternships(expire_in_two_months)
        result['expire_in_two_months_percentage'] = "{0:.0f}%".format(
            operator.truediv(result['expire_in_two_months_count'], result['active_count']) * 100) \
            if result['active_count'] and result['expire_in_two_months_count'] else "0%"

        return Response(result, status=status.HTTP_200_OK)
