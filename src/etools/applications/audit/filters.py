from django.contrib.auth import get_user_model
from django.db import models
from django.db.models.functions import TruncYear

from django_filters import rest_framework as filters
from rest_framework.filters import BaseFilterBackend

from etools.applications.audit.models import Engagement
from etools.applications.organizations.models import Organization


class DisplayStatusFilter(BaseFilterBackend):
    """
    Filter engagements by display status instead of database status value.
    """

    def filter_queryset(self, request, queryset, view):
        status = request.query_params.get('status')
        if not status:
            status = request.query_params.get('status__in')
        if not status:
            return queryset

        statuses = status.split(',')
        filters = models.Q()

        for status in statuses:
            if status in [
                Engagement.STATUSES.report_submitted,
                Engagement.STATUSES.final,
                Engagement.STATUSES.cancelled
            ]:
                filters |= models.Q(status=status)
            if status == Engagement.DISPLAY_STATUSES.partner_contacted:
                filters |= models.Q(status=Engagement.STATUSES.partner_contacted, date_of_field_visit__isnull=True)
            elif status == Engagement.DISPLAY_STATUSES.field_visit:
                filters |= models.Q(status=Engagement.STATUSES.partner_contacted,
                                    date_of_field_visit__isnull=False, date_of_draft_report_to_ip__isnull=True)
            elif status == Engagement.DISPLAY_STATUSES.draft_issued_to_partner:
                filters |= models.Q(status=Engagement.STATUSES.partner_contacted,
                                    date_of_draft_report_to_ip__isnull=False, date_of_comments_by_ip__isnull=True)
            elif status == Engagement.DISPLAY_STATUSES.comments_received_by_partner:
                filters |= models.Q(status=Engagement.STATUSES.partner_contacted,
                                    date_of_comments_by_ip__isnull=False, date_of_draft_report_to_unicef__isnull=True)
            elif status == Engagement.DISPLAY_STATUSES.draft_issued_to_unicef:
                filters |= models.Q(status=Engagement.STATUSES.partner_contacted,
                                    date_of_draft_report_to_unicef__isnull=False,
                                    date_of_comments_by_unicef__isnull=True)
            elif status == Engagement.DISPLAY_STATUSES.comments_received_by_unicef:
                filters |= models.Q(status=Engagement.STATUSES.partner_contacted,
                                    date_of_comments_by_unicef__isnull=False)
        return queryset.filter(filters)


class UniqueIDOrderingFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        ordering = request.query_params.get('ordering', '')
        if not ordering.lstrip('-') == 'reference_number':
            return queryset

        ordering_params = ['partner__organization__name', 'engagement_type', 'created_year', 'id']

        return queryset.annotate(created_year=TruncYear('created'))\
            .order_by(*map(lambda param: ('' if ordering == 'reference_number' else '-') + param, ordering_params))


class EngagementFilter(filters.FilterSet):
    sections__in = filters.BaseInFilter(field_name="sections")
    offices__in = filters.BaseInFilter(field_name="offices")
    # TODO: REALMS - test updated filters
    staff_members__user__exact = filters.CharFilter(field_name="staff_members__id")
    staff_members__user__in = filters.BaseInFilter(field_name="staff_members")

    class Meta:
        model = Engagement
        fields = {
            'agreement': ['exact'],
            'agreement__auditor_firm': ['exact', 'in'],
            'partner': ['exact', 'in'],
            'engagement_type': ['exact', 'in'],
            'joint_audit': ['exact'],
            'agreement__auditor_firm__unicef_users_allowed': ['exact'],
            'partner_contacted_at': ['lte', 'gte', 'gt', 'lt'],
            'date_of_draft_report_to_ip': ['lte', 'gte', 'gt', 'lt'],
            'offices': ['exact', 'in'],
            'sections': ['exact', 'in'],
        }


class AuditorStaffMembersFilterSet(filters.FilterSet):
    user__profile__countries_available__name = filters.CharFilter(field_name='realms__country__name', distinct=True)

    class Meta:
        model = get_user_model()
        fields = {}


class UnicefUsersAllowedFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        unicef_users_allowed = request.query_params.get(
            'purchase_order_auditorstaffmember__auditor_firm__unicef_users_allowed',
            '',
        ).lower()
        if unicef_users_allowed not in ['true', 'false']:
            return queryset

        unicef_filter = models.Q(profile__organization=Organization.objects.get(name='UNICEF'))

        if unicef_users_allowed == 'true':
            return queryset.filter(unicef_filter)
        else:
            return queryset.filter(~unicef_filter)
