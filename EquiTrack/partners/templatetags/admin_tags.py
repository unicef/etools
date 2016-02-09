__author__ = 'Robi'


import tablib

from django import template

from users.models import (
    Country
)

register = template.Library()


@register.simple_tag
def show_country_select(value):

    if not value:
        return ''

    countries = Country.objects.all()

    html = ''
    for country in countries:
        if country.name == value:
            html += '<option value="'+str(country.id)+'" selected>'+country.name+'</option>'
        else:
            html += '<option value="'+str(country.id)+'">'+country.name+'</option>'

    return '<select id="country_selection">' + html + '</select>'
