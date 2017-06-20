import datetime
import operator

from django.shortcuts import get_object_or_404
from django.contrib.auth import models
from django.db.models.functions import Concat, Value
from django.db.models import F

from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import IsAdminUser
from rest_framework.views import APIView

from publics.models import Currency

from reports.models import (
    ResultStructure,
    CountryProgramme,
    Result,
    ResultType,
)
from supplies.models import SupplyItem
from funds.models import Donor

from partners.models import (
    PartnerOrganization,
    PCA,
    Agreement,
    PartnerStaffMember,
    PartnerType,
    Assessment,
    InterventionAmendment,
    AgreementAmendmentType,
    Intervention,
    FileType,
)
from partners.serializers.partner_organization_v2 import (
    PartnerStaffMemberDetailSerializer,
    PartnerStaffMemberPropertiesSerializer,
    PartnerStaffMemberCreateUpdateSerializer,
)
from partners.permissions import PartneshipManagerPermission, PartnerPermission
from partners.serializers.v1 import InterventionSerializer
from partners.filters import PartnerScopeFilter


class PartnerInterventionListAPIView(ListAPIView):
    queryset = Intervention.objects.all()
    serializer_class = InterventionSerializer
    permission_classes = (PartnerPermission,)

    def list(self, request, pk=None, format=None):
        """
        Return All Interventions for Partner
        """
        interventions = Intervention.objects.filter(partner_id=pk)
        serializer = InterventionSerializer(interventions, many=True)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )


class AgreementInterventionsListAPIView(ListAPIView):
    serializer_class = InterventionSerializer
    filter_backends = (PartnerScopeFilter,)
    permission_classes = (PartneshipManagerPermission,)

    def list(self, request, partner_pk=None, pk=None, format=None):
        """
        Return All Interventions for Partner and Agreement
        """
        if partner_pk:
            interventions = PCA.objects.filter(partner_id=partner_pk, agreement_id=pk)
        else:
            interventions = PCA.objects.filter(agreement_id=pk)
        serializer = InterventionSerializer(interventions, many=True)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )


class PartnerStaffMemberDetailAPIView(RetrieveUpdateDestroyAPIView):
    queryset = PartnerStaffMember.objects.all()
    serializer_class = PartnerStaffMemberDetailSerializer
    permission_classes = (PartneshipManagerPermission,)
    filter_backends = (PartnerScopeFilter,)

    def get_serializer_class(self, format=None):
        if self.request.method in ["PUT", "PATCH"]:
            return PartnerStaffMemberCreateUpdateSerializer
        return super(PartnerStaffMemberDetailAPIView, self).get_serializer_class()


class PartnerStaffMemberPropertiesAPIView(RetrieveAPIView):
    """
    Gets the details of Staff Member that belongs to a partner
    """
    serializer_class = PartnerStaffMemberPropertiesSerializer
    queryset = PartnerStaffMember.objects.all()
    permission_classes = (PartneshipManagerPermission,)

    def get_object(self):
        queryset = self.get_queryset()

        # Get the current partnerstaffmember
        try:
            current_member = PartnerStaffMember.objects.get(id=self.request.user.profile.partner_staff_member)
        except PartnerStaffMember.DoesNotExist:
            raise Exception('there is no PartnerStaffMember record associated with this user')

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        # If current member is actually looking for themselves return right away.
        if self.kwargs[lookup_url_kwarg] == str(current_member.id):
            return current_member

        filter = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        # allow lookup only for PSMs inside the same partnership
        filter['partner'] = current_member.partner

        obj = get_object_or_404(queryset, **filter)
        self.check_object_permissions(self.request, obj)
        return obj


def choices_to_json_ready(choices):

    if isinstance(choices, dict):
        choice_list = [[k, v] for k, v in choices]
        # return list(set(x.values(), ))
    elif isinstance(choices, tuple):
        choice_list = choices
    elif isinstance(choices, list):
        choice_list = []
        for c in choices:
            if isinstance(c, tuple):
                choice_list.append([c[0], c[1]])
            else:
                choice_list.append([c, c])
    else:
        choice_list = []
    final_list = []
    for choice in choice_list:
        final_list.append({'label': choice[1], 'value': choice[0]})
    return final_list


class PmpStaticDropdownsListApiView(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request):
        """
        Return All Static values used for dropdowns in the frontend
        """

        local_workspace = self.request.user.profile.country
        cso_types = choices_to_json_ready(
            list(
                PartnerOrganization.objects.values_list(
                    'cso_type',
                    flat=True).order_by('cso_type').distinct('cso_type')))
        partner_types = choices_to_json_ready(tuple(PartnerType.CHOICES))
        agency_choices = choices_to_json_ready(tuple(PartnerOrganization.AGENCY_CHOICES))
        assessment_types = choices_to_json_ready(Assessment.ASSESMENT_TYPES)
        agreement_types = choices_to_json_ready(
            [typ for typ in Agreement.AGREEMENT_TYPES if typ[0] not in ['IC', 'AWP']])
        agreement_status = choices_to_json_ready(Agreement.STATUS_CHOICES)
        agreement_amendment_types = choices_to_json_ready(tuple(AgreementAmendmentType.AMENDMENT_TYPES))
        intervention_doc_type = choices_to_json_ready(Intervention.INTERVENTION_TYPES)
        intervention_status = choices_to_json_ready(Intervention.INTERVENTION_STATUS)
        intervention_amendment_types = choices_to_json_ready(InterventionAmendment.AMENDMENT_TYPES)

        currencies = map(lambda x: {"label": x[0], "value": x[1]},
                         Currency.objects.values_list('code', 'id').order_by('code').distinct())

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
                'local_currency': local_currency
            },
            status=status.HTTP_200_OK
        )


class PMPDropdownsListApiView(APIView):
    # serializer_class = InterventionSerializer
    # filter_backends = (PartnerScopeFilter,)
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

        hrps = list(ResultStructure.objects.values())
        current_country_programme = CountryProgramme.current()
        cp_outputs = list(Result.objects.filter(result_type__name=ResultType.OUTPUT, wbs__isnull=False,
                                                country_programme=current_country_programme).values('id', 'name', 'wbs'))
        supply_items = list(SupplyItem.objects.all().values())
        file_types = list(FileType.objects.all().values())
        donors = list(Donor.objects.all().values())

        return Response(
            {
                'signed_by_unicef_users': signed_by_unicef,
                'hrps': hrps,
                'cp_outputs': cp_outputs,
                'supply_items': supply_items,
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
            interventions = Intervention.objects.filter(agreement__country_programme=ct_pk)

        # Otherwise, use current CountryProgramme this year to filter Intervention
        else:
            currentCountryProgramme = CountryProgramme.current()

            interventions = Intervention.objects.filter(
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
