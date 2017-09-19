from django.core.management import BaseCommand
from datetime import date, datetime, timedelta
from users.models import Country, User
from partners.models import *
from funds.models import *
from EquiTrack.util_scripts import *


class Command(BaseCommand):
    help = 'A set of scripts that checks the data models for anything that ' \
           'does not fit within the new pmp redesign models'

    def handle(self, *args, **options):
        run(active_pca_no_signed_doc)  # ported
        run(pd_outputs_wrong)
        run(pd_frs_not_found)
        run(interventions_associated_ssfa)
        run(intervention_update_task)
        run(interventions_amendments_no_file)
        run(agreement_amendments_no_file)


# pd frs not found
# run before migrations
def pd_frs_not_found():
    if not hasattr(Intervention, 'fr_numbers'):
        # this attribute doesn't seem to exist
        print('No fr_numbers attribute found. Skipping this step.')
        return
    for i in Intervention.objects.all():
        fr_numbers = i.fr_numbers if i.fr_numbers else []
        for fr in fr_numbers:
            try:
                fr_obj = FundsReservationHeader.objects.get(fr_number=fr)
            except FundsReservationHeader.DoesNotExist:
                if i.status != 'draft':
                    # workaround in the local db until records are fixed in production
                    printtf('{}, {} FR not found for Intervention {}'.format(i.status, fr, i.id))
            else:
                if fr_obj.intervention and fr_obj.intervention.id != i.id:
                    printtf('#### {}, FR {} connected to a different Intervention {}... current Intervention {}'.
                            format(i.status, fr_obj.fr_number, fr_obj.intervention.id, i.id))


# pca no attachment
def active_pca_no_signed_doc():
    issue_id = 'active_pca_no_signed_doc'
    for agr in Agreement.objects.filter(agreement_type=Agreement.PCA).exclude(status='draft'):
        if not agr.attached_agreement:
            print(message)


# pd wrong cp outputs
def pd_outputs_wrong():
    cps = CountryProgramme.objects.filter(invalid=False, wbs__contains='/A0/')
    for cp in cps:
        interventions = Intervention.objects.filter(start__gte=cp.from_date, start__lte=cp.to_date)
        for intervention in interventions:
            wrong_cp = []
            for rl in intervention.result_links.all():
                if rl.cp_output.country_programme != cp:
                    wrong_cp.append(rl.cp_output.wbs)
            if len(wrong_cp) > 0:

                print ("PD [P{}] STATUS [{}] CP [{}] has wrongly mapped outputs {}".format(intervention.id, intervention.status, cp.wbs, wrong_cp))


# PDs attached to SSFA agreements
def interventions_associated_ssfa():
    intervention_pds_ssfa = Intervention.objects.filter(agreement__agreement_type=Agreement.SSFA, document_type=Intervention.PD)
    intervention_ssfa_pca = Intervention.objects.filter(agreement__agreement_type=Agreement.PCA,
                                                        document_type=Intervention.SSFA)
    interventions = intervention_pds_ssfa | intervention_ssfa_pca
    for i in interventions:
        print('intervention {} type {} status {} has agreement type {}'.format(i.id, i.document_type, i.status, i.agreement.agreement_type))

# PD amendments missing files
def interventions_amendments_no_file():
    ias = InterventionAmendment.objects.filter(signed_amendment='')
    for amd in ias:
        print('intervention {} type {} status {} has missing amendment file'.format(amd.intervention.id, amd.intervention.document_type, amd.intervention.status))

# PCA amendments missing files
def agreement_amendments_no_file():
    aas = AgreementAmendment.objects.filter(signed_amendment='')
    for amd in aas:
        print('agreement {} type {} status {} has missing amendment file'.format(amd.agreement.id, amd.agreement.agreement_type, amd.agreement.status))
