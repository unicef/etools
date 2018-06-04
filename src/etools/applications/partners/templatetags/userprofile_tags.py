
from django import template
from django.conf import settings
from django.utils import six
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag(takes_context=True)
def show_country_select(context, profile):

    if not profile:
        return ''
    countries = profile.countries_available.all().order_by('name')  # Country.objects.all()

    if 'opts' in context and context['opts'].app_label in settings.TENANT_APPS:
        countries = countries.exclude(schema_name='public')

    html = ''
    for country in countries:
        if country == profile.country:
            html += '<option value="' + six.text_type(country.id) + '" selected>' + country.name + '</option>'
        else:
            html += '<option value="' + six.text_type(country.id) + '">' + country.name + '</option>'

    return mark_safe('<select id="country_selection">' + html + '</select>')


@register.simple_tag(takes_context=True)
def tenant_model_filter(context, app):
    if hasattr(context.request, 'tenant'):
        tenant_app_labels = [app.split('.')[-1] for app in settings.TENANT_APPS]
        return not (context.request.tenant.schema_name == 'public' and app['app_label'] in tenant_app_labels)
    return True


@register.simple_tag()
def tenant_app_filter(app):
    tenant_app_labels = [app.split('.')[-1] for app in settings.TENANT_APPS]
    return app['app_label'] in tenant_app_labels
