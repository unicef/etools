from partners.models import PartnerOrganization


class HiddenPartnerMixin(object):

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == u'partner':
            kwargs['queryset'] = PartnerOrganization.objects.filter(hidden=False)

        return super(HiddenPartnerMixin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )
