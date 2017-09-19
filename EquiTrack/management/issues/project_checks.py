from .checks import BaseIssueCheck, ModelCheckData
from management.issues.exceptions import IssueFoundException
from partners.models import Agreement, Intervention


# todo: these can probably move closer to the models they are associated with, but just
# starting with them here as a proof of concept
from reports.models import CountryProgramme


class ActivePCANoSignedDocCheck(BaseIssueCheck):
    model = Agreement
    issue_id = 'active-pca-no-signed-doc'

    def get_queryset(self):
        return Agreement.objects.filter(agreement_type=Agreement.PCA).exclude(status='draft')

    def run_check(self, model_instance, metadata):
        if not model_instance.attached_agreement:
            raise IssueFoundException(
                '{} Agreement [{}] does not have a signed PCA attached'.format(model_instance.agreement_type,
                                                                               model_instance.id)
            )


class PdOutputsWrongCheck(BaseIssueCheck):
    model = Intervention
    issue_id = 'pd_outputs_wrong'

    def get_objects_to_check(self):
        cps = CountryProgramme.objects.filter(invalid=False, wbs__contains='/A0/')
        for cp in cps:
            interventions = Intervention.objects.filter(
                start__gte=cp.from_date, start__lte=cp.to_date
            ).prefetch_related('result_links')
            for intervention in interventions:
                yield ModelCheckData(intervention, {'cp': cp})

    def run_check(self, model_instance, metadata):
        wrong_cp = []
        cp = metadata['cp']
        for rl in model_instance.result_links.all():
            if rl.cp_output.country_programme != cp:
                wrong_cp.append(rl.cp_output.wbs)
        if len(wrong_cp) > 0:
            raise IssueFoundException(
                "PD [P{}] STATUS [{}] CP [{}] has wrongly mapped outputs {}".format(
                    model_instance.id, model_instance.status, cp.wbs, wrong_cp)
            )
