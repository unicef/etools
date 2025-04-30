from django.db import models
from django.db.models import Q

from django_filters import rest_framework as filters
from rest_framework.filters import BaseFilterBackend

from etools.applications.organizations.models import Organization
from etools.applications.users.models import Realm


class UserRoleFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if 'roles' in request.query_params and request.query_params['roles']:
            filter_q = Q()
            for role in request.query_params['roles'].split(','):
                filter_l = Q(group__id=role, is_active=True)
                filter_q |= filter_l

            qs_context = getattr(view, 'qs_context', None)

            realm_ids = list(
                Realm.objects.filter(**qs_context).filter(filter_q)
                .select_related('group')
                .values_list('id', flat=True)
            )

            return queryset.filter(realms__id__in=realm_ids)

        return queryset


class UserStatusFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if queryset and 'status' in request.query_params and request.query_params['status']:
            status_list = [status.strip().lower() for status in request.query_params['status'].split(',')]
            filters = models.Q()
            for status in status_list:
                if status == 'inactive':
                    filters |= models.Q(is_active=False)
                if status == 'active':
                    filters |= models.Q(is_active=True, last_login__isnull=False, has_active_realm=True)
                if status == 'invited':
                    filters |= models.Q(is_active=True, last_login__isnull=True, has_active_realm=True)
                if status == 'no access':
                    filters |= models.Q(is_active=True, has_active_realm=False)
            return queryset.filter(filters)
        return queryset


class OrganizationFilter(filters.FilterSet):
    organization_id = filters.NumberFilter()
    organization_type = filters.ChoiceFilter(choices=(('audit', 'audit'), ('partner', 'partner'), ('tpm', 'tpm')))

    class Meta:
        model = Organization
        fields = ['organization_id', 'organization_type']

    def filter_queryset(self, queryset):
        return queryset
