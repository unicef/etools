from django.contrib.admin.options import flatten_fieldsets
from django.contrib.auth.models import Group

from partners.models import PartnerOrganization


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
                        if new_field not in fields:
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


class HiddenPartnerMixin(object):

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == u'partner':
            kwargs['queryset'] = PartnerOrganization.objects.filter(hidden=False)

        return super(HiddenPartnerMixin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )
