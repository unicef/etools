__author__ = 'unicef'

from EquiTrack.utils import BaseEmail


class PartnershipCreatedEmail(BaseEmail):

    template_name = 'partners/partnership/created/updated'
    description = ('The email that is sent when a partnership'
                   ' is added or is updated')
    subject = 'Partnership {{number}} has been {{state}}'
    content = """
    Dear Colleague,

    Partnership {{number}} has been {{state}} here:

    {{url}}

    Thank you.
    """

    def get_context(self):
        return {
            'number': self.object.__unicode__(),
            'state': 'Created',
            'url': 'https://{}{}'.format(
                self.get_current_site().domain,
                self.object.get_admin_url()
            )
        }


class PartnershipUpdatedEmail(PartnershipCreatedEmail):

    def get_context(self):
        context = super(PartnershipUpdatedEmail, self).get_context()
        context['state'] = 'Updated'
        return context
