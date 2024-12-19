from django import template

from etools.applications.last_mile import models

register = template.Library()


@register.filter
def all_items(transfer):
    return models.Item.all_objects.filter(transfer=transfer)
