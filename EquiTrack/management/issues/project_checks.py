from .checks import BaseIssueCheck
from management.issues.exceptions import IssueFoundException
from partners.models import Agreement


# todo: these can probably move closer to the models they are associated with, but just
# starting with them here as a proof of concept


class ActivePCANoSignedDocCheck(BaseIssueCheck):
    model = Agreement
    issue_id = 'active-pca-no-signed-doc'

    def get_queryset(self):
        return Agreement.objects.filter(agreement_type=Agreement.PCA).exclude(status='draft')

    def run_check(self, model_instance):
        if not model_instance.attached_agreement:
            raise IssueFoundException(
                '{} Agreement [{}] does not have a signed PCA attached'.format(model_instance.agreement_type,
                                                                               model_instance.id)
            )
