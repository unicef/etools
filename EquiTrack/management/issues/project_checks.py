from django.contrib.auth.models import User
from django.db.models import Q
from .checks import BaseIssueCheck, ModelCheckData
from management.issues.exceptions import IssueFoundException
from partners.models import Agreement, Intervention


# todo: these can probably move closer to the models they are associated with, but just
# starting with them here as a proof of concept
from partners.validation.interventions import InterventionValid
from reports.models import CountryProgramme


class ActivePCANoSignedDocCheck(BaseIssueCheck):
    model = Agreement
    issue_id = 'active_pca_no_signed_doc'

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


class InterventionsAssociatedSSFACheck(BaseIssueCheck):
    model = Intervention
    issue_id = 'interventions_associated_ssfa'

    def get_queryset(self):
        return Intervention.objects.filter(
            Q(agreement__agreement_type=Agreement.SSFA, document_type=Intervention.PD) |
            Q(agreement__agreement_type=Agreement.PCA, document_type=Intervention.SSFA)
        ).prefetch_related('agreement')

    def run_check(self, model_instance, metadata):
        # in this case the queryset controls the issue, so all relevant objects should fail,
        # but we still need the test to be inside `run_check` so that objects can be rechecked
        # in the future
        fails_test = (
            (
                model_instance.agreement.agreement_type == Agreement.SSFA
                and model_instance.document_type == Intervention.PD
            )
            or (
                model_instance.agreement.agreement_type == Agreement.PCA
                and model_instance.document_type == Intervention.SSFA
            )
        )
        if fails_test:
            raise IssueFoundException(
                'intervention {} type {} status {} has agreement type {}'.format(
                    model_instance.id, model_instance.document_type,
                    model_instance.agreement.agreement_type, model_instance.status
                )
            )


class InterventionsAreValidCheck(BaseIssueCheck):
    model = Intervention
    issue_id = 'interventions_are_valid'

    def get_objects_to_check(self):
        master_user = User.objects.get(username='etools_task_admin')
        for intervention in Intervention.objects.filter(status__in=['draft', 'signed', 'active', 'ended']):
            yield ModelCheckData(intervention, {'master_user': master_user})

    def run_check(self, model_instance, metadata):
        master_user = metadata['master_user']
        validator = InterventionValid(model_instance, master_user)
        if not validator.is_valid:
            raise IssueFoundException(
                'intervention {} of type {} is invalid: (Status:{}), Errors: {}'.format(
                    model_instance.id, model_instance.document_type, model_instance.status,
                    ', '.join(validator.errors)
                )
            )
