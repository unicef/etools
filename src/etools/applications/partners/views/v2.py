import datetime
import operator

from django.contrib.auth import get_user_model
from django.db.models import Value
from django.db.models.functions import Concat

from model_utils import Choices
from rest_framework import status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from unicef_attachments.models import FileType as AttachmentFileType

from etools.applications.attachments.models import AttachmentFlat
from etools.applications.funds.models import FundsReservationItem
from etools.applications.governments.models import GDDRisk
from etools.applications.locations.models import Location
from etools.applications.partners.models import (
    Agreement,
    AgreementAmendment,
    Assessment,
    FileType,
    Intervention,
    InterventionAmendment,
    InterventionRisk,
    OrganizationType,
    PartnerOrganization,
)
from etools.applications.partners.permissions import SENIOR_MANAGEMENT_GROUP
from etools.applications.reports.models import CountryProgramme, Result, ResultType
from etools.libraries.djangolib.fields import CURRENCIES


# TODO move in core (after utils package has been merged in core)
def choices_to_json_ready(choices, sort_choices=True):
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

    if sort_choices:
        choice_list = sorted(choice_list, key=lambda tup: tup[1])
    return [{'label': choice[1], 'value': choice[0]} for choice in choice_list]


class PMPStaticDropdownsListAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        """
        Return All Static values used for dropdowns in the frontend
        """

        local_workspace = self.request.user.profile.country
        cso_types = PartnerOrganization.objects.values_list('cso_type', flat=True)
        cso_types = cso_types.exclude(cso_type__isnull=True).exclude(cso_type__exact='')
        cso_types = cso_types.order_by('cso_type').distinct('cso_type')
        cso_types = choices_to_json_ready(list(cso_types))
        partner_types = choices_to_json_ready(OrganizationType.CHOICES)
        agency_choices = choices_to_json_ready(PartnerOrganization.AGENCY_CHOICES)
        partner_risk_rating = choices_to_json_ready(PartnerOrganization.RISK_RATINGS)
        assessment_types = choices_to_json_ready(Assessment.ASSESSMENT_TYPES)
        agreement_types = choices_to_json_ready(Agreement.AGREEMENT_TYPES)
        agreement_status = choices_to_json_ready(Agreement.STATUS_CHOICES, sort_choices=False)
        agreement_amendment_types = choices_to_json_ready(AgreementAmendment.AMENDMENT_TYPES)
        intervention_doc_type = choices_to_json_ready(Intervention.INTERVENTION_TYPES)
        intervention_status = choices_to_json_ready(Intervention.INTERVENTION_STATUS, sort_choices=False)
        intervention_amendment_types = choices_to_json_ready(InterventionAmendment.AMENDMENT_TYPES)
        location_types = Location.objects.values('admin_level_name', 'admin_level').order_by('admin_level').distinct()
        currencies = choices_to_json_ready(CURRENCIES)
        attachment_types = AttachmentFileType.objects.values_list(
            "label",
            flat=True,
        )
        attachment_types_active = AttachmentFlat.get_file_types()
        partner_file_types = FileType.objects.values_list("name", flat=True)
        sea_risk_ratings = choices_to_json_ready(PartnerOrganization.ALL_COMBINED_RISK_RATING)
        gender_equity_sustainability_ratings = choices_to_json_ready(Intervention.RATING_CHOICES, sort_choices=False)
        risk_types = choices_to_json_ready(InterventionRisk.RISK_TYPE_CHOICES, sort_choices=False)
        gpd_risk_types = choices_to_json_ready(GDDRisk.RISK_TYPE_CHOICES, sort_choices=False)
        cash_transfer_modalities = choices_to_json_ready(Intervention.CASH_TRANSFER_CHOICES, sort_choices=False)

        local_currency = local_workspace.local_currency.id if local_workspace.local_currency else None

        return Response(
            {
                'cso_types': cso_types,
                'partner_types': partner_types,
                'agency_choices': agency_choices,
                'partner_risk_rating': partner_risk_rating,
                'assessment_types': assessment_types,
                'agreement_types': agreement_types,
                'agreement_status': agreement_status,
                'agreement_amendment_types': agreement_amendment_types,
                'intervention_doc_type': intervention_doc_type,
                'intervention_status': intervention_status,
                'intervention_amendment_types': intervention_amendment_types,
                'currencies': currencies,
                'local_currency': local_currency,
                'location_types': location_types,
                'attachment_types': attachment_types,
                'attachment_types_active': attachment_types_active,
                'partner_file_types': partner_file_types,
                'sea_risk_ratings': sea_risk_ratings,
                'gender_equity_sustainability_ratings': gender_equity_sustainability_ratings,
                'gpd_risk_types': gpd_risk_types,
                'risk_types': risk_types,
                'cash_transfer_modalities': cash_transfer_modalities,
            },
            status=status.HTTP_200_OK
        )


class PMPDropdownsListApiView(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser)

    def get(self, request):
        """
        Return All dropdown values used for Agreements form
        """
        signed_by_unicef = list(get_user_model().objects.filter(
            realms__group__name__in=[SENIOR_MANAGEMENT_GROUP],
            profile__country=request.user.profile.country
        ).annotate(
            name=Concat('first_name', Value(' '), 'last_name')
        ).values('id', 'name', 'username', 'email'))

        country_programmes = list(CountryProgramme.objects.all_active_and_future.values('id', 'wbs', 'name',
                                                                                        'from_date', 'to_date'))
        cp_outputs = [{"id": r.id, "name": r.output_name, "wbs": r.wbs, "country_programme": r.country_programme.id}
                      for r in Result.objects.filter(result_type__name=ResultType.OUTPUT, wbs__isnull=False)]
        file_types = list(FileType.objects.filter(name__in=[i[0] for i in FileType.NAME_CHOICES])
                          .all().values())

        donors = FundsReservationItem.objects.filter(donor__isnull=False).\
            order_by('donor').values_list('donor', flat=True).distinct('donor')
        grants = FundsReservationItem.objects.filter(donor__isnull=False).\
            order_by('grant_number').values_list('grant_number', flat=True).distinct('grant_number')

        return Response(
            {
                'signed_by_unicef_users': signed_by_unicef,
                'country_programmes': country_programmes,
                'cp_outputs': cp_outputs,
                'file_types': file_types,
                'donors': choices_to_json_ready(list(donors), sort_choices=False),
                'grants': choices_to_json_ready(list(grants), sort_choices=False)
            },
            status=status.HTTP_200_OK
        )


class PartnershipDashboardAPIView(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser)

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
            OrganizationType.BILATERAL_MULTILATERAL,
            OrganizationType.CIVIL_SOCIETY_ORGANIZATION,
            OrganizationType.UN_AGENCY,
        ]:
            result['partners'][p_type] = active_partnerships.filter(
                agreement__partner__partner_type=p_type).count()

        # Count GovernmentInterventions separately
        result['partners'][OrganizationType.GOVERNMENT] = 0

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
