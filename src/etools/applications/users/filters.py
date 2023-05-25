from django.db import models

from rest_framework.filters import BaseFilterBackend


class UserRoleFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if 'roles' in request.query_params and request.query_params['roles']:
            return queryset.filter(realms__group__id__in=request.query_params['roles'].split(',')).distinct()
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
