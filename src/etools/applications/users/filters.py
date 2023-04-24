from django.db import models

from rest_framework.filters import BaseFilterBackend


class UserRoleFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if 'roles' in request.query_params and request.query_params['roles']:
            return queryset.filter(realms__group__id__in=request.query_params['roles'].split(',')).distinct()
        return queryset


class UserStatusFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if 'status' in request.query_params and request.query_params['status']:
            queryset = queryset.prefetch_related('realms')
            status_list = [status.strip().upper() for status in request.query_params['status'].split(',')]
            filters = models.Q()
            for status in status_list:
                if status == 'INACTIVE':
                    filters |= models.Q(is_active=False)
                if status == 'ACTIVE':
                    filters |= models.Q(is_active=True, last_login__isnull=False)
                if status == 'INVITED':
                    filters |= models.Q(is_active=True, last_login__isnull=True)
                if status == 'INOPERATIVE':
                    filters |= models.Q(is_active=True, realms__is_active=False)
            return queryset.filter(filters)
        return queryset
