from __future__ import print_function
from string import translate
import json
from django.db import connection
from django.db.models import Count
import time
from datetime import datetime, timedelta
from users.models import Country
from reports.models import ResultType, Result, CountryProgramme, Indicator, ResultStructure, LowerResult
from partners.models import FundingCommitment, PCA, InterventionPlannedVisits, AuthorizedOfficer, BankDetails, \
    AgreementAmendmentLog, AgreementAmendment, Intervention, AmendmentLog, InterventionAmendment, RAMIndicator, \
    InterventionResultLink, PartnershipBudget, InterventionBudget, InterventionAttachment, PCAFile, Sector, \
    InterventionSectorLocationLink, SupplyPlan, DistributionPlan

def printtf(*args):
    print([arg for arg in args])
    f = open('mylogs.txt','a')
    print([arg for arg in args], file=f)
    f.close()

def set_country(name):
    connection.set_tenant(Country.objects.get(name=name))


def fix_duplicate_indicators(country_name):
    if not country_name:
        printtf("country name required /n")
    set_country(country_name)
    printtf("Fixing duplicate indicators for {}".format(country_name))
    fattrs = ["ramindicator_set"]

    def fix_indicator_code():
        printtf('cleaning codes of indicators for country ', country_name)
        indicators = Indicator.objects.filter(code__exact='').all()
        for ind in indicators:
            ind.code = None
            ind.save()
        time.sleep(3)
    fix_indicator_code()


    def relates_to_anything(cobj):
        for a in fattrs:
            if getattr(cobj, a).count():
                printtf(cobj.id, cobj, "relates to ", a)
                return True
        return False
    def update_relationships(dpres, keep):
        for a in fattrs:
            objs = getattr(dpres, a).all()
            if len(objs):
                for obj in objs:
                    obj.indicator = keep
                    obj.save()
                    printtf("saved obj.id={} obj {} with keepid{} keep {}".format(obj.id, obj, keep.id, keep))

    def _run_clean(dupes):
        printtf(len(dupes), dupes)
        for dup in dupes:
            dupresults = Indicator.objects.filter(code=dup['code'], result=dup['result']).all()
            delq = []
            keep = None
            for dpres in dupresults:
                if not keep:
                    keep = dpres
                    continue
                else:
                    error = False
                    if relates_to_anything(dpres):
                        try:
                            update_relationships(dpres, keep)
                        except Exception as exp:
                            printtf('Cannot remove Object {}, id={}'.format(dpres, dpres.id))
                            error = True
                    if error:
                        printtf("ERROR OCCURED ON RECORD", dpres.id, dpres)
                        continue
                    delq.append(dpres)
            if not len(delq):
                printtf("Nothing is getting removed for {}".format(dupes))
            else:
                # delete everyting in the queue
                [i.delete() for i in delq]
                printtf("deleting: ", delq)

    dupes = Indicator.objects.values('code', 'result').order_by('code', 'result').annotate(Count('pk')).filter(pk__count__gt=1, ram_indicator=True).all()
    _run_clean(dupes)

def fix_duplicate_results(country_name):

    if not country_name:
        printtf("country name required /n")
    set_country(country_name)
    printtf("Fixing duplicate Results for {}".format(country_name))
    # foreign attributes
    fattrs = ["governmentinterventionresult_set",
            "indicator_set",
            "ramindicator_set",
            "resultchain_set",
            "tripfunds_set"]
    fattrs_mapping = {
        "governmentinterventionresult_set": "result",
        "indicator_set" : "result",
        "ramindicator_set": "result",
        "resultchain_set": "result",
        "tripfunds_set": "wbs"
    }
    def fix_string_wbs():
        results = Result.objects.filter(wbs__exact='').all()
        for res in results:
            res.wbs = None
            res.save()
    fix_string_wbs()

    def reparent_children(current_object, new_parent):
        for child in current_object.get_children():
            child.parent = new_parent
            printtf( "reparenting child", child.id, child, new_parent.id, new_parent)
            child.save()
    def relates_to_anything(cobj):
        for a in fattrs:
            if getattr(cobj, a).count():
                printtf(cobj.id, cobj, "relates to ", a)
                return True
        return False
    def update_relationships(dpres, keep):
        for a in fattrs:
            objs = getattr(dpres, a).all()
            if len(objs):
                for obj in objs:
                    if a == "tripfunds_set":
                        obj.wbs = keep
                    else:
                        obj.result = keep
                    obj.save()
                    printtf("saved obj.id={} obj {} with keepid{} keep {}".format(obj.id, obj, keep.id, keep))
    def _run_clean(prop, dupes):
        printtf(len(dupes), dupes)
        search_string = prop + '__exact'
        for dup in dupes:
            dupresults = Result.objects.prefetch_related('result_type').filter(**{search_string: dup[prop]}).all()
            delq = []
            keep = None
            for dpres in dupresults:
                if not keep:
                    keep = dpres
                    continue
                else:
                    error = False
                    if dpres.get_children():
                        try:
                            reparent_children(dpres, keep)
                        except Exception as exp:
                            printtf('Cannot reparent from Object {}, id={}'.format(dpres, dpres.id))
                            error = True
                    if relates_to_anything(dpres):
                        try:
                            update_relationships(dpres, keep)
                        except Exception as exp:
                            printtf('Cannot remove Object {}, id={}'.format(dpres, dpres.id))
                            error = True
                    if error:
                        printtf("ERROR OCCURED ON RECORD", dpres.id, dpres)
                        continue
                    delq.append(dpres)
            time.sleep(0.3)
            if not len(delq):
                printtf("Nothing is getting removed for {}".format(dupes))
            else:
                # delete everyting in the queue
                [i.delete() for i in delq]
                printtf("deleting: ", delq)
    # get all duplicates that have the same wbs
    dupes = Result.objects.values('wbs').annotate(Count('wbs')).order_by().filter(wbs__count__gt=1, wbs__isnull=False).exclude(wbs__exact='').all()
    dupes = sorted(dupes, key=lambda x: x['wbs'].count('/'), reverse=True)
    _run_clean('wbs', dupes)

def cp_fix(country_name):
    if not country_name:
        printtf("country name required /n")
    set_country(country_name)
    printtf("Fixing Country Programme for {}".format(country_name))
    def get_cpwbs(wbs):
        grp = wbs.split('/')
        return '/'.join(grp[:3])

    results = Result.objects.filter(wbs__isnull=False).exclude(wbs__exact='')
    locpwbs = []
    for res in results:
        cpwbs = get_cpwbs(res.wbs)
        if cpwbs not in locpwbs:
            locpwbs.append(cpwbs)

    today = datetime.now()
    for i in range(len(locpwbs)):
        today = today + timedelta(days=i)
        tomorrow = today + timedelta(days=365)
        cp, created = CountryProgramme.objects.get_or_create(wbs=locpwbs[i], name='Country Programme '+str(i), from_date=today, to_date=tomorrow)

    time.sleep(5)

    for res in results:
        cp = CountryProgramme.objects.get(wbs=get_cpwbs(res.wbs))
        res.country_programme = cp
        res.save()
        print(res.name)

def clean_result_types(country_name):
    if not country_name:
        printtf("country name required /n")
        set_country(country_name)
    if not country_name:
        printtf("country name required /n")

    set_country(country_name)
    printtf("Fixing duplicate Result Types for {}".format(country_name))
    fattrs = ["result_set"]

    def relates_to_anything(cobj):
        for a in fattrs:
            if getattr(cobj, a).count():
                printtf(cobj.id, cobj, "relates to ", a)
                return True
        return False

    def update_relationships(dpres, keep):
        for a in fattrs:
            objs = getattr(dpres, a).all()
            if len(objs):
                for obj in objs:
                    obj.result_type = keep
                    obj.save()
                    printtf("saved obj.id={} obj {} with keepid{} keep {}".format(obj.id, obj, keep.id, keep))

    def _run_clean(dupes):
        printtf(len(dupes), dupes)
        for dup in dupes:
            dupresults = ResultType.objects.filter(name=dup['name']).all()
            delq = []
            keep = None
            for dpres in dupresults:
                if not keep:
                    keep = dpres
                    continue
                else:
                    error = False
                    if relates_to_anything(dpres):
                        try:
                            update_relationships(dpres, keep)
                        except Exception as exp:
                            printtf('Cannot remove Object {}, id={}'.format(dpres, dpres.id))
                            error = True
                    if error:
                        printtf("ERROR OCCURED ON RECORD", dpres.id, dpres)
                        continue
                    delq.append(dpres)
            if not len(delq):
                printtf("Nothing is getting removed for {}".format(dupes))
            else:
                # delete everyting in the queue
                [i.delete() for i in delq]
                printtf("deleting: ", delq)

    # get all duplicates that have the same wbs
    dupes = ResultType.objects.values('name').annotate(Count('name')).order_by().filter(name__count__gt=1).all()
    _run_clean(dupes)

def clean_result_structures(country_name):
    if not country_name:
        printtf("country name required /n")
        set_country(country_name)
    if not country_name:
        printtf("country name required /n")

    set_country(country_name)
    printtf("Fixing duplicate Result Structures for {}".format(country_name))
    fattrs = ["result_set",
              "indicator_set",
              "goal_set",
              "pca_set",
              "governmentintervention_set", ]

    def relates_to_anything(cobj):
        for a in fattrs:
            if getattr(cobj, a).count():
                printtf(cobj.id, cobj, "relates to ", a)
                return True
        return False

    def update_relationships(dpres, keep):
        for a in fattrs:
            objs = getattr(dpres, a).all()
            if len(objs):
                for obj in objs:
                    obj.result_structure = keep
                    obj.save()
                    printtf("saved obj.id={} obj {} with keepid{} keep {}".format(obj.id, obj, keep.id, keep))

    def _run_clean(dupes):
        printtf(len(dupes), dupes)
        for dup in dupes:
            dupresults = ResultStructure.objects.filter(name=dup['name']).all()
            delq = []
            keep = None
            for dpres in dupresults:
                if not keep:
                    keep = dpres
                    continue
                else:
                    error = False
                    if relates_to_anything(dpres):
                        try:
                            update_relationships(dpres, keep)
                        except Exception as exp:
                            printtf('Cannot remove Object {}, id={}'.format(dpres, dpres.id))
                            error = True
                    if error:
                        printtf("ERROR OCCURED ON RECORD", dpres.id, dpres)
                        continue
                    delq.append(dpres)
            if not len(delq):
                printtf("Nothing is getting removed for {}".format(dupes))
            else:
                # delete everyting in the queue
                [i.delete() for i in delq]
                printtf("deleting: ", delq)

    # get all duplicates that have the same name
    dupes = ResultStructure.objects.values('name', 'from_date', 'to_date').order_by('name', 'from_date', 'to_date').annotate(Count('pk')).filter(pk__count__gt=1).all()
    _run_clean(dupes)


def delete_all_fcs(country_name):
    if not country_name:
        printtf("country name required /n")
    set_country(country_name)
    printtf("Deleting all FCs for {}".format(country_name))
    fcs = FundingCommitment.objects.all()
    fcs.delete()

def dissasociate_result_structures(country_name):
    if not country_name:
        printtf("country name required /n")
    set_country(country_name)
    printtf("Dissasociating result structures for {}".format(country_name))
    results = Result.objects.all()
    for result in results:
        if result.wbs and result.result_structure:
            result.result_structure = None
            result.save()


def all_countries_do(function, name):
    for cntry in Country.objects.order_by('name').all():
        if cntry.name in ['Global']:
            continue
        printtf("CALLING {} for all countries".format(name))
        function(cntry.name)


def before_code_merge():
    # Clean results
    all_countries_do(fix_duplicate_results, 'Result Cleaning')

    # Clean results structure
    all_countries_do(clean_result_structures, 'Result Structure Cleaning')

    # clean result types
    all_countries_do(clean_result_types, 'Result Types Cleaning')

    # Clean indicators
    all_countries_do(fix_duplicate_indicators, 'Indicators Cleaning')

    # Delete all fcs
    all_countries_do(delete_all_fcs, 'Deleting FCs')

    print('FINISHED WITH BEFORE MERGE')


def after_code_merge(): #and after migrations

    # set up country programme
    all_countries_do(cp_fix, 'Country Programme setup')

    # disassociate result structures
    all_countries_do(dissasociate_result_structures, 'Dissasociate Result Structure')

    print("don't forget to sync")

def migrate_authorized_officers():
    """
    Migrates AuthorizedOfficer from schema  , cntryinstances back to the Agreement as a M2M field
    to PartnerStaffMember
    """
    for cntry in Country.objects.order_by('name').exclude(name='Global'):
        set_country(cntry.name)
        authorized_officers = AuthorizedOfficer.objects.all()
        for item in authorized_officers:
            agreement = item.agreement
            officer = item.officer
            agreement.authorized_officers.add(officer)
            agreement.save()

from partners.models import Agreement


def populate_reference_numbers():
    for cntry in Country.objects.exclude(name__in=['Global']).order_by('name').all():
        set_country(cntry)
        pcas = PCA.objects.filter(number__isnull=True, signed_by_unicef_date__isnull=False).exclude(
            status=PCA.DRAFT)
        print(cntry.name)
        print(pcas)
        for pca in pcas:
            pca.number = pca.reference_number
            pca.save()

        agreements = Agreement.objects.filter(signed_by_unicef_date__isnull=False, agreement_number__isnull=True)
        for agr in agreements:
            agr.agreement_number = agr.reference_number
            agr.save()

# run this before migration partners_0005
def agreement_unique_reference_number():
    for cntry in Country.objects.exclude(name__in=['Global']).order_by('name').all():
        set_country(cntry)
        print(cntry.name)
        agreements = Agreement.objects.all()
        for agr in agreements:
            if agr.agreement_number == '':
                print(agr)
                agr.agreement_number = 'blk:{}'.format(agr.id)
                agr.save()
        dupes = Agreement.objects.values('agreement_number').annotate(Count('agreement_number')).order_by().filter(agreement_number__count__gt=1).all()
        for dup in dupes:
            cdupes = Agreement.objects.filter(agreement_number=dup['agreement_number'])
            for cdup in cdupes:
                cdup.agreement_number = '{}|{}'.format(cdup.agreement_number, cdup.id)
                print(cdup)
                cdup.save()

def pca_unique_reference_number():
    from django.db.models import signals
    signals.post_save.disconnect(receiver=PCA.send_changes, sender=PCA)
    for cntry in Country.objects.exclude(name__in=['Global']).order_by('name').all():
        set_country(cntry)
        print(cntry.name)
        pcas = PCA.objects.all()
        for pca in pcas:
            if not pca.number:
                print(pca)
                pca.number = 'blk:{}'.format(pca.id)
                pca.save()
        dupes = PCA.objects.values('number').annotate(
            Count('number')).order_by().filter(number__count__gt=1).all()
        for dup in dupes:
            cdupes = PCA.objects.filter(number=dup['number'])
            for cdup in cdupes:
                if len(cdup.number) > 40:
                    cdup.number = cdup.number[len(cdup.number)-40:]
                cdup.number = '{}|{}'.format(cdup.number, cdup.id)
                print(cdup)
                cdup.save()
    signals.post_save.connect(receiver=PCA.send_changes, sender=PCA)

#run this after migration partners_0006
def bank_details_to_partner():
    for cntry in Country.objects.exclude(name__in=['Global']).order_by('name').all():
        set_country(cntry)
        print(cntry.name)
        bds = BankDetails.objects.all()
        if bds.count() > 0:
            for bd in bds:
                if not bd.partner_organization:
                    bd.partner_organization = bd.agreement.partner
                    print(bd.partner_organization.name)
                    bd.save()

        # agreement model bank details
        # agreements = Agreement.objects.filter(bank_name__isnull=False).exclude(bank_name='')
        # if agreements.count() > 0:
        #     print("================ AGREEMENTS MODEL ================================")
        #     for agr in agreements:
        #         bd, created = BankDetails.objects.get_or_create(agreement=agr,
        #                                                         partner_organization=agr.partner,
        #                                                         bank_name=agr.bank_name,
        #                                                         bank_address= agr.bank_address,
        #                                                         account_title=agr.account_title,
        #                                                         account_number=agr.account_number,
        #                                                         routing_details=agr.routing_details,
        #                                                         bank_contact_person=agr.bank_contact_person)
        #         if created:
        #             print(bd.partner_organization)

#run this after migration partners_0007
def agreement_amendments_copy():
    for cntry in Country.objects.exclude(name__in=['Global']).order_by('name').all():
        set_country(cntry)
        print(cntry.name)
        agr_amds = AgreementAmendmentLog.objects.all()
        amd_type = ''
        for amd in agr_amds:
            if amd.type == 'Authorised Officers':
                amd_type = 'Change authorized officer'
            elif amd.type == 'Banking Info':
                amd_type = 'Change banking info'
            elif amd.type == 'Agreement Changes':
                amd_type = 'Amend existing clause'
            elif amd.type == 'Additional Clauses':
                amd_type = 'Additional clause'

            agr_amd, created = AgreementAmendment.objects.get_or_create(number=amd.amendment_number,
                                                                        agreement=amd.agreement,
                                                                        type=amd_type,
                                                                        signed_amendment=amd.signed_document,
                                                                        signed_date=amd.amended_at )
            if created:
                print('{}-{}'.format(agr_amd.number, agr_amd.agreement))


def copy_pca_fields_to_intervention():
    MAPPING = {
        'created_at': 'created',
        'updated_at': 'modified',
        'partnership_type': 'document_type',
        'number': 'number',
        'title': 'title',
        'status': 'status',
        'start_date': 'start',
        'end_date': 'end',
        'initiation_date': 'submission_date',
        'submission_date': 'submission_date_prc',
        'review_date': 'review_date_prc',
        'signed_by_unicef_date': 'signed_by_unicef_date',
        'signed_by_partner_date': 'signed_by_partner_date',
        'agreement': 'agreement',
        'result_structure': 'hrp',
        'partner_manager': 'partner_authorized_officer_signatory',
        'unicef_manager': 'unicef_signatory',
    }
    status_map = {
        'in_proccess': 'Draft'
    }
    pca_attrs = ['created_at', 'updated_at', 'partnership_type', 'number', 'title', 'status', 'start_date', 'end_date',
                 'initiation_date', 'submission_date', 'review_date', 'signed_by_unicef_date', 'signed_by_partner_date',
                 'agreement', 'result_structure', 'partner_manager', 'unicef_manager']
    for cntry in Country.objects.exclude(name__in=['Global']).order_by('name').all():
        set_country(cntry)
        print(cntry)
        pcas = PCA.objects.all()
        interventions_to_save = []
        for pca in pcas:
            if pca.number == '-':
                print('-')
            if pca.partnership_type in [PCA.AWP, PCA.IC]:
                continue
            intervention = Intervention()
            for attr in pca_attrs:
                if attr == 'status' and pca.status == u'in_process':
                    setattr(intervention, 'status', u'draft')
                elif attr == 'agreement' and not getattr(pca, attr):
                    break
                else:
                    setattr(intervention, MAPPING[attr], getattr(pca, attr))
            if not intervention.document_type:
                continue
            try:
                if intervention.status in \
                        [intervention.ACTIVE, intervention.SUSPENDED, intervention.TERMINATED, intervention.IMPLEMENTED] \
                        and \
                        not intervention.signed_by_unicef_date:
                    if intervention.start:
                        intervention.signed_by_unicef_date = intervention.start
                    elif intervention.signed_by_partner_date:
                        intervention.signed_by_unicef_date = intervention.signed_by_partner_date
                    else:
                        intervention.signed_by_unicef_date = intervention.created
                print('before', intervention, intervention.status, intervention.document_type)
                if not intervention.agreement:
                    continue
                interventions_to_save.append(intervention)
            except Exception as e:
                print(pca.number)
                print(intervention.number)
                raise e
            print('after', intervention, intervention.status, intervention.document_type)
        Intervention.objects.bulk_create(interventions_to_save)

def clean_interventions():
    for country in Country.objects.exclude(name='Global'):
        set_country(country)
        Intervention.objects.all().delete()


def copy_pca_amendments_to_intervention():
    for cntry in Country.objects.exclude(name__in=['Global']).order_by('name').all():
        set_country(cntry)
        print(cntry)
        amendments = AmendmentLog.objects.all()
        for amendment in amendments:
            amd_type = ''
            if amendment.type == 'No Cost':
                amd_type = InterventionAmendment.CTBLT20
            if amendment.type == 'Cost':
                amd_type = InterventionAmendment.CTBGT20
            if amendment.type == 'Activity':
                amd_type = InterventionAmendment.CABGT20
            if amendment.type == 'Other':
                amd_type = InterventionAmendment.CPR
            try:
                intervention = Intervention.objects.get(number=amendment.partnership.number)
            except Intervention.DoesNotExist:
                continue

            intr_amd, created = InterventionAmendment.objects.get_or_create(signed_date=amendment.amended_at,
                                                                        intervention=intervention,
                                                                        type=amd_type,
                                                                        amendment_number=amendment.amendment_number)
            if created:
                print('{}-{}'.format(intr_amd.amendment_number, intr_amd.intervention))


def export_old_pca_fields():
    pca_fields = {}
    for cntry in Country.objects.exclude(name__in=['Global']).order_by('name').all():
        set_country(cntry)
        pcas = PCA.objects.all()
        numbers = []
        for pca in pcas:
            if pca.fr_number or pca.planned_visits > 0:
                pca_numbers = {}
                pca_numbers['pca'] = pca.number
                pca_numbers['fr_number'] = pca.fr_number or 0
                pca_numbers['planned_visits'] = pca.planned_visits
                numbers.append(pca_numbers)
        print(numbers)
        if numbers.count > 0:
            pca_fields[cntry.name] = numbers
    print(pca_fields)

    with open('pca_numbers.json', 'w') as fp:
        json.dump(pca_fields, fp)


def import_planned_visits():
    with open('pca_numbers.json') as data_file:
        data = json.load(data_file)
        for country, array in data.items():
            if array:
                set_country(country)
                for row in array:
                    try:
                        intervention = Intervention.objects.get(number=row['pca'])
                    except Intervention.DoesNotExist:
                        continue
                    if intervention.planned_visits > 0 and intervention.start:
                        InterventionPlannedVisits.objects.get_or_create(intervention=intervention,
                                                            year=intervention.start.year,
                                                            programmatic=row['planned_visits'])

def import_fr_numbers():
    with open('pca_numbers.json') as data_file:
        data = json.load(data_file)
        for country, array in data.items():
            if array:
                set_country(country)
                for row in array:
                    try:
                        intervention = Intervention.objects.get(number=row['pca'])
                    except Intervention.DoesNotExist:
                        continue
                    intervention.fr_numbers = [row['fr_number']]
                    intervention.save()


def copy_pca_results_to_intervention():
    for cntry in Country.objects.exclude(name__in=['Global']).order_by('name').all():
        set_country(cntry)
        print(cntry)
        for pca in PCA.objects.all():
            result_ids = pca.indicators.order_by().values_list('result__id', flat=True).distinct()
            for result_id in result_ids:
                result = Result.objects.get(id=result_id)
                ram_inds = pca.indicators.filter(result=result)
                indicators = []
                for ram_ind in ram_inds:
                    if ram_ind.indicator:
                        indicators.append(ram_ind.indicator)
                try:
                    intervention = Intervention.objects.get(number=pca.number)
                except Intervention.DoesNotExist:
                    print(pca.number)
                    continue
                irl, created = InterventionResultLink.objects.get_or_create(intervention=intervention, cp_output=result)
                irl.ram_indicators.add(*indicators)


def copy_pca_budgets_to_intervention():
    for cntry in Country.objects.exclude(name__in=['Global']).order_by('name').all():
        set_country(cntry)
        print(cntry)
        for pca in PCA.objects.all():
            pb_years = pca.budget_log.values_list('year', flat=True).distinct()
            if not pb_years:
                continue
            try:
                intervention = Intervention.objects.get(number=pca.number)
            except Intervention.DoesNotExist:
                print(pca.number)
                continue
            print(pb_years)
            for pb_year in pb_years:
                if pb_year:
                    pb = pca.budget_log.filter(year=pb_year).order_by('-created').first()
                    InterventionBudget.objects.get_or_create(intervention=intervention,
                                                            partner_contribution=pb.partner_contribution,
                                                            unicef_cash=pb.unicef_cash,
                                                            in_kind_amount=pb.in_kind_amount,
                                                            year=pb.year)

def copy_pca_attachments_to_intervention():
    for cntry in Country.objects.exclude(name__in=['Global']).order_by('name').all():
        set_country(cntry)
        print(cntry)
        for pca_file in PCAFile.objects.all():
            try:
                intervention = Intervention.objects.get(number=pca_file.pca.number)
            except Intervention.DoesNotExist:
                print(pca_file.pca.number)
                continue
            InterventionAttachment.objects.get_or_create(intervention=intervention,
                                                         type=pca_file.type,
                                                         attachment=pca_file.attachment)

def copy_pca_sector_locations_to_intervention():
    for cntry in Country.objects.exclude(name__in=['Global']).order_by('name').all():
        set_country(cntry)
        print(cntry)
        for pca in PCA.objects.all():
            sector_ids = pca.locations.order_by().values_list('sector__id', flat=True).distinct()
            for sector_id in sector_ids:
                if not sector_id:
                    continue
                sector = Sector.objects.get(id=sector_id)
                gwpc_locations = pca.locations.filter(sector=sector)
                locations = []
                for location in gwpc_locations:
                    if location.location:
                        locations.append(location.location)
                try:
                    intervention = Intervention.objects.get(number=pca.number)
                except Intervention.DoesNotExist:
                    print(pca.number)
                    continue
                isl, created = InterventionSectorLocationLink.objects.get_or_create(intervention=intervention,
                                                                                    sector=sector)
                isl.locations.add(*locations)

def copy_pca_supply_plan_to_intervention():
    for cntry in Country.objects.exclude(name__in=['Global']).order_by('name').all():
        set_country(cntry)
        print(cntry)
        for sp in SupplyPlan.objects.all():
            try:
                intervention = Intervention.objects.get(number=sp.partnership.number)
            except Intervention.DoesNotExist:
                print(sp.partnership.number)
                continue
            sp.intervention = intervention
            sp.save()

def copy_pca_distribution_plan_to_intervention():
    for cntry in Country.objects.exclude(name__in=['Global']).order_by('name').all():
        set_country(cntry)
        print(cntry)
        for dp in DistributionPlan.objects.all():
            if SupplyPlan.objects.filter(intervention=dp.intervention, item=dp.item).count():
                try:
                    intervention = Intervention.objects.get(number=dp.partnership.number)
                except Intervention.DoesNotExist:
                    print(dp.partnership.number)
                    continue
                dp.intervention = intervention
                dp.save()


def local_country_keep():
    set_country('Global')
    keeping = ['Global', 'UAT', 'Lebanon', 'Syria', 'Indonesia', 'Sudan', 'Syria Cross Border']
    Country.objects.exclude(name__in=keeping).all().delete()


from partners.models import GovernmentIntervention
def gov_int_copy_rs_to_cp():
    for gi in GovernmentIntervention:
        try:
            gi.country_programme = CountryProgramme.encapsulates(gi.result_structure.from_date, gi.result_structure.to_date)
            gi.save()
        except:
            pass


def after_partner_migration():
    copy_pca_fields_to_intervention()
    agreement_amendments_copy()
    copy_pca_results_to_intervention()
    copy_pca_attachments_to_intervention()


