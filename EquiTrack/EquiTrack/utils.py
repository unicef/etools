__author__ = 'jcranwellward'

from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse

admin_url_name = 'admin:{app_label}_{model_name}_{action}'


class AdminURLMixin(object):
    def get_admin_url(self):
        content_type = ContentType \
            .objects \
            .get_for_model(self.__class__)
        return reverse(admin_url_name.format(
            app_label=content_type.app_label,
            model_name=content_type.model,
            action='change'
        ), args=(self.id,))


def get_changeform_link(model, link_name='View', action='change'):
    if model.id:
        url_name = admin_url_name.format(
            app_label=model._meta.app_label,
            model_name=model._meta.model_name,
            action=action
        )
        changeform_url = reverse(url_name, args=(model.id,))
        return u'<a class="btn btn-primary default" ' \
               u'onclick="return showAddAnotherPopup(this);" ' \
               u'href="{}" target="_blank">{}</a>'.format(changeform_url, link_name)
    return u''
