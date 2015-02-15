__author__ = 'jcranwellward'

from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse


class AdminURLMixin(object):

    admin_url_name = 'admin:{app_label}_{model_name}_{action}'

    def get_admin_url(self):
        content_type = ContentType \
            .objects \
            .get_for_model(self.__class__)
        return reverse(self.admin_url_name.format(
            app_label=content_type.app_label,
            model_name=content_type.model,
            action='change'
        ), args=(self.id,))