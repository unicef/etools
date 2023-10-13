from django.contrib.auth import get_user_model
from django.db import connection

from etools.applications.partners.models import PartnerOrganization


class HiddenPartnerMixin:

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'partner':
            kwargs['queryset'] = PartnerOrganization.objects.filter(hidden=False)

        return super().formfield_for_foreignkey(
            db_field, request, **kwargs
        )


class CountryUsersAdminMixin:

    staff_only = True

    def filter_users(self, kwargs):

        filters = {}
        if self.staff_only:
            filters['is_staff'] = True

        if filters:
            # preserve existing filters if any
            queryset = kwargs.get("queryset", get_user_model().objects.select_related(None))
            kwargs["queryset"] = queryset.filter(**filters).distinct()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.remote_field.model is get_user_model():
            self.filter_users(kwargs)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.remote_field.model is get_user_model():
            self.filter_users(kwargs)

        return super().formfield_for_manytomany(db_field, request, **kwargs)
