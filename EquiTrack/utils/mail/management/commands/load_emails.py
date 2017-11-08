from __future__ import unicode_literals

import types

from django.core.management.commands.loaddata import Command as LoaddataCommand

from post_office.models import EmailTemplate


class Command(LoaddataCommand):
    help = "Simple loaddata command with workaround for emailtemplate naturalkey support. " \
           "Required until https://github.com/ui/django-post_office/pull/198 is not merged"

    def handle(self, *fixture_labels, **options):

        if not hasattr(EmailTemplate._default_manager, 'get_by_natural_key'):
            def get_by_natural_key(self, name, language, default_template):
                return self.get(name=name, language=language, default_template=default_template)

            default_manager = EmailTemplate._default_manager
            default_manager.get_by_natural_key = types.MethodType(get_by_natural_key, default_manager)

            def natural_key(self):
                return (self.name, self.language, self.default_template)

            EmailTemplate.natural_key = natural_key

        super(Command, self).handle(*fixture_labels, **options)
