from django.db import connection, models
from django.db.models import Q

from django_filters import rest_framework as filters
from rest_framework.filters import BaseFilterBackend

from etools.applications.organizations.models import Organization


class UserRoleFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if 'roles' in request.query_params and request.query_params['roles']:
            filter_q = Q()
            for role in request.query_params['roles'].split(','):
                filter_l = Q(realms__group__id=role, realms__is_active=True)
                filter_q |= filter_l
            queryset = queryset.filter(filter_q)

            query = str(queryset.query)
            search_text = 'INNER JOIN "users_realm"'
            search = query.rfind(search_text) + len(search_text) + 1
            alias_for_user_realm_table = query[search:search + 2]

            search_text = 'INNER JOIN "auth_group"'
            search = query.rfind(search_text) + len(search_text) + 1
            alias_for_auth_group_table = query[search:search + 2]

            with (connection.cursor() as cursor):
                query = query.replace('INNER JOIN "users_realm" ' + alias_for_user_realm_table +
                                      ' ON ("auth_user"."id" = ' + alias_for_user_realm_table + '."user_id")', ""
                                      ).replace(alias_for_user_realm_table, '"users_realm"')

                query = query.replace(' AND ' + alias_for_auth_group_table + '."name" IN '
                                                                             '(IP Viewer, IP Editor, IP Authorized Officer, IP Admin, IP LM Editor)', "")

                query = query.replace(' AND ' + alias_for_auth_group_table + '."name" IN '
                                                                             '(IP Viewer, IP Editor, IP Authorized Officer, IP Admin, IP LM Editor)', "")

                cursor.execute(query)

                user_ids = [row[0] for row in cursor.fetchall()]

            return queryset.filter(id__in=user_ids).distinct()

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
