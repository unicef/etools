from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag(takes_context=True)
def show_country_select(context, profile):

    if not profile:
        return ''
    countries = profile.countries_available.all()  # Country.objects.all()

    if 'opts' in context and context['opts'].app_label in settings.TENANT_APPS:
        countries = countries.exclude(schema_name='public')

    html = ''
    for country in countries:
        if country == profile.country:
            html += '<option value="' + str(country.id) + '" selected>' + country.name + '</option>'
        else:
            html += '<option value="' + str(country.id) + '">' + country.name + '</option>'

    return mark_safe('<select id="country_selection">' + html + '</select>')


@register.simple_tag(takes_context=True)
def tenant_model_filter(context, app_name):
    return not (context.request.tenant.schema_name == 'public' and app_name in settings.TENANT_APPS)
