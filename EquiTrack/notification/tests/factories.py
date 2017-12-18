import json

import factory

from notification import models as notification_models
from partners.tests.factories import AgreementFactory


# Credit goes to http://stackoverflow.com/a/41154232/2363915
class JSONFieldFactory(factory.DictFactory):

    @classmethod
    def _build(cls, model_class, *args, **kwargs):
        if args:
            raise ValueError(
                "DictFactory %r does not support Meta.inline_args.", cls)
        return json.dumps(model_class(**kwargs))


class NotificationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = notification_models.Notification

    type = "Email"
    sender = factory.SubFactory(AgreementFactory)
    template_name = 'trips/trip/TA_request'
    recipients = ['test@test.com', 'test1@test.com', 'test2@test.com']
    template_data = factory.Dict(
        {
            'url': 'www.unicef.org',
            'pa_assistant': 'Test revised',
            'owner_name': 'Tester revised'
        },
        dict_factory=JSONFieldFactory
    )
