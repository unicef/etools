from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

from etools import NAME, VERSION
from etools.applications.core.util_scripts import currency_format

register = template.Library()


@register.simple_tag
def etools_version():
    return mark_safe('{}: v{}'.format(NAME, VERSION))


@register.simple_tag
def vision_url():
    return settings.INSIGHT_URL


@register.simple_tag(takes_context=True)
def show_country_select(context, user):

    if not user:
        return ''
    # only countries from active realms are in the dropdown list
    countries = user.profile.countries_available.order_by('name')

    if 'opts' in context and context['opts'].app_label in settings.TENANT_APPS:
        countries = countries.exclude(schema_name='public')

    html = ''
    for country in countries:
        if country == user.profile.country:
            html += '<option value="' + str(country.id) + '" selected>' + country.name + '</option>'
        else:
            html += '<option value="' + str(country.id) + '">' + country.name + '</option>'

    return mark_safe('<select id="country_selection">' + html + '</select>')


@register.simple_tag(takes_context=True)
def tenant_model_filter(context, app):
    if hasattr(context.request, 'tenant'):
        tenant_app_labels = [tenant_app.split('.')[-1] for tenant_app in settings.TENANT_APPS]
        return not (context.request.tenant.schema_name == 'public' and app['app_label'] in tenant_app_labels)
    return True


@register.simple_tag()
def tenant_app_filter(app):
    tenant_app_labels = [tenant_app.split('.')[-1] for tenant_app in settings.TENANT_APPS]
    return app['app_label'] in tenant_app_labels


@register.simple_tag
def call_method(obj, method_name, *args):
    method = getattr(obj, method_name)
    return method(*args)


@register.filter(is_safe=True)
def currency(value):
    return currency_format(value)
