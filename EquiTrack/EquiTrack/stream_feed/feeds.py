from django.utils.feedgenerator import rfc3339_date
from django.utils.six import text_type

from actstream.feeds import JSONActivityFeed, CustomStreamMixin


class JSONActivityFeedWithCustomData(CustomStreamMixin, JSONActivityFeed):

    def format(self, action):
        """
        Overriden to add a custom data per each item to render.
        Returns a formatted dictionary for the given action.
        """
        item = {
            'id': self.get_uri(action),
            'url': self.get_url(action),
            'verb': action.verb,
            'published': rfc3339_date(action.timestamp),
            'actor': self.format_actor(action),
            'title': text_type(action),
        }
        if action.description:
            item['content'] = action.description
        if action.target:
            item['target'] = self.format_target(action)
        if action.action_object:
            item['object'] = self.format_action_object(action)
        if action.data:
            item['data'] = action.data

        return item
