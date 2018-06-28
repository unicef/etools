from django.template import Origin, TemplateDoesNotExist
from django.template.loaders.base import Loader as BaseLoader

from post_office.models import EmailTemplate
from post_office.utils import get_email_template

EMAIL_TEMPLATE_PREFIX = 'email-templates/'


class EmailTemplateLoader(BaseLoader):
    def get_template_sources(self, template_name):
        if not template_name.startswith(EMAIL_TEMPLATE_PREFIX):
            return

        yield Origin(
            name=template_name[len(EMAIL_TEMPLATE_PREFIX):],
            template_name=template_name,
            loader=self,
        )

    def load_template_source(self, template_name, template_dirs=None):
        for origin in self.get_template_sources(template_name):
            try:
                template = get_email_template(origin.name)
                return template.html_content, origin.name
            except EmailTemplate.DoesNotExist:
                pass
        raise TemplateDoesNotExist(template_name)
