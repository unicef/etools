
__author__ = 'jcranwellward'

import re

from django.contrib.admin.options import flatten_fieldsets
from django.contrib.auth.models import Group

from partners.models import PCASector





class ReadOnlyMixin(object):
    """
    Mixin class to force all fields to readonly
    if a user is in the read_only group
    """
    read_only_group_name = u'read_only'
    remove_fields_if_read_only = ()

    def remove_from_fieldsets(self, fieldsets, fields):
        for fieldset in fieldsets:
            for field in fields:
                if field in fieldset[1]['fields']:
                    new_fields = []
                    for new_field in fieldset[1]['fields']:
                        if not new_field in fields:
                            new_fields.append(new_field)

                    fieldset[1]['fields'] = tuple(new_fields)
                    break

    def get_readonly_fields(self, request, obj=None):

        read_only, created = Group.objects.get_or_create(
            name=self.read_only_group_name
        )
        if obj and read_only in request.user.groups.all():

            if self.declared_fieldsets:
                fieldsets = self.declared_fieldsets
                self.remove_from_fieldsets(fieldsets, self.remove_fields_if_read_only)
                fields = flatten_fieldsets(fieldsets)
            else:
                fields = list(set(
                    [field.name for field in self.opts.local_fields] +
                    [field.name for field in self.opts.local_many_to_many]
                ))
            return fields

        return self.readonly_fields


class SectorMixin(object):
    """
    Mixin class to get the sector from the admin URL
    """
    model_admin_re = re.compile(r'^/admin/(?P<app>\w*)/(?P<model>\w*)/(?P<id>\w+)/$')

    def get_sector_from_request(self, request):
        results = self.model_admin_re.search(request.path)
        if results:
            pca_sector_id = results.group('id')
            return PCASector.objects.get(id=pca_sector_id)
        return None

    def get_sector(self, request):
        if not getattr(self, '_sector', False):
            self._sector = self.get_sector_from_request(request).sector
        return self._sector

    def get_pca(self, request):
        if not getattr(self, '_pca', False):
            self._pca = self.get_sector_from_request(request).pca
        return self._pca