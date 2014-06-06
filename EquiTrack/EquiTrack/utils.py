__author__ = 'jcranwellward'

from django.core import urlresolvers


def get_changeform_link(model, link_name='View', action='change'):
    if model.id:
        url_name = 'admin:{app_label}_{model_name}_{action}'.format(
            app_label=model._meta.app_label,
            model_name=model._meta.model_name,
            action=action
        )
        changeform_url = urlresolvers.reverse(url_name, args=(model.id,))
        return u'<a class="btn btn-primary default" ' \
               u'onclick="return showAddAnotherPopup(this);" ' \
               u'href="{}" target="_blank">{}</a>'.format(changeform_url, link_name)
    return u''