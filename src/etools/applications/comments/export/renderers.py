from django.utils.translation import ugettext_lazy as _

from etools.applications.core.renderers import FriendlyCSVRenderer, ListSeperatorCSVRenderMixin


class CommentCSVRenderer(ListSeperatorCSVRenderMixin, FriendlyCSVRenderer):

    header = [
        'id', 'created', 'user', 'state', 'users_related',
        'related_to_description', 'related_to', 'text',
    ]
    labels = {
        'id': _('ID'),
        'created': _('Created'),
        'user': _('User'),
        'state': _('State'),
        'users_related': _('Users Related'),
        'related_to': _('Related To'),
        'related_to_description': _('Related To (description)'),
        'text': _('Text'),
    }
