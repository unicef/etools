import datetime
import json
import logging

from django.db import transaction
from django.db.models import Q
from etools.applications.governments.models import GovernmentEWP, EWPOutput, EWPKeyIntervention
from etools.applications.locations.models import Location
from etools.applications.partners.models import PartnerOrganization

from unicef_vision.exceptions import VisionException
from unicef_vision.settings import INSIGHT_DATE_FORMAT

from etools.applications.reports.models import CountryProgramme, Result, ResultType
from etools.applications.vision.synchronizers import VisionDataTenantSynchronizer
from unicef_vision.synchronizers import FileDataSynchronizer

logger = logging.getLogger(__name__)

# Existing classes:


class EWPSynchronizer:

    def __init__(self, data):
        self.data = data
        self.workplans = {}
        self.ewp_outputs = {}
        self.ewp_key_interventions = {}
        self.activities = {}
        # TODO for the following assert that there are no
        # discrepancies in length. There should be no values missing from the db
        self.cps = {r.wbs: r for r in
                    CountryProgramme.objects.filter(wbs__in=self.data['remote_cps'])}
        self.outputs = {r.wbs: r for r in
                        Result.objects.filter(wbs__in=[r["wbs"] for r in self.data['remote_outputs']], result_type__name=ResultType.OUTPUT)}
        self.kis = {r.wbs: r for r in
                    Result.objects.filter(wbs__in=[r["wbs"] for r in self.data['remote_kis']], result_type__name=ResultType.ACTIVITY)}
        self.locations = {r.p_code: r for r in Location.objects.filter(p_code__in=self.data['remote_locations'])}
        self.partners = {r.organization.vendor_number: r for r in PartnerOrganization.objects.filter(
            organization__vendor_number__in=self.data['remote_partners'])}

    @staticmethod
    def _update_changes(local, remote):
        updated = False
        for k in remote:
            if getattr(local, k) != remote[k]:
                updated = True
                setattr(local, k, remote[k])

        return updated

    def _get_local_parent(self, wbs, parent_type):
        parent_map = {
            # 10 is the number of characters for a cp wbs
            'cp': (10, self.cps),
            'outcome': (14, self.outcomes),
            'output': (18, self.outputs)
        }
        parent_group = parent_map[parent_type][1]
        wbs_length = parent_map[parent_type][0]
        return parent_group.get(wbs[:wbs_length], None)

    def update_workplans(self):
        remote_ewps = self.data['remote_ewps']
        total_data = len(remote_ewps)
        total_updated = 0

        local_ewps = {record.wbs: record for record in GovernmentEWP.objects.filter(wbs__in=list(remote_ewps.keys()))}
        for local_ewp in local_ewps.values():
            if self._update_changes(local_ewp, remote_ewps[local_ewp.wbs]):
                logger.debug('Updated {}'.format(local_ewp))
                total_updated += 1
                local_ewp.save()
            del remote_ewps[local_ewp.wbs]

        # Normally a bulk save, but in this case there are very few records, and things are calculated on save:
        new_ewps = {}
        for remote_ewp in remote_ewps.values():
            remote_ewp['country_programme'] = self.cps[remote_ewp['country_programme']]
            new_ewps[remote_ewp['wbs']], _ = GovernmentEWP.objects.get_or_create(**remote_ewp)

        # add the newly created cps
        local_ewps.update(new_ewps)
        self.workplans = local_ewps

        return total_data, total_updated, len(new_ewps)

    def update_ewp_outputs(self):
        remote_ewp_outputs = self.data['remote_outputs']
        total_data = len(remote_ewp_outputs)
        total_updated = 0

        query = Q()
        for item in remote_ewp_outputs:
            query |= Q(cp_output__wbs=item["wbs"], workplan__wbs=item["workplan"])

        local_ewp_outputs = {f'{record.cp_output.wbs}{record.workplan.wbs}': record for record in EWPOutput.objects.filter(query)}

        new_remote_outputs = [item for item in remote_ewp_outputs if item["wbs"] not in local_ewp_outputs.keys()]

        new_outputs = {}
        for remote_output in new_remote_outputs:
            new_outputs[f'{remote_output["wbs"]}{remote_output['workplan']}'], _ = EWPOutput.objects.get_or_create(cp_output=self.outputs[remote_output['wbs']],
                                            workplan=self.workplans[remote_output['workplan']],)

        local_ewp_outputs.update(new_outputs)
        self.ewp_outputs = local_ewp_outputs
        return total_data, total_updated, len(new_outputs)

    def update_kis(self):
        remote_ewp_kis = self.data['remote_kis']
        total_data = len(remote_ewp_kis)
        total_updated = 0

        query = Q()
        for item in remote_ewp_kis:
            query |= Q(cp_key_intervention__wbs=item["wbs"],
                       ewp_output__cp_output__wbs=item["output"],
                       ewp_output__workplan__wbs=item["workplan"])

        local_ewp_kis = {f'{record.cp_key_intervention.wbs}{record.ewp_output.workplan.wbs}':
                             record for record in EWPKeyIntervention.objects.filter(query)}

        new_remote_kis = [item for item in remote_ewp_kis if item["wbs"] not in local_ewp_kis.keys()]

        new_kis = {}
        for remote_ki in new_remote_kis:
            new_kis[f'{remote_ki["wbs"]}{remote_ki['workplan']}'], _ = EWPKeyIntervention.objects.get_or_create(
                cp_key_intervention=self.kis[remote_ki['wbs']],
                ewp_output=self.ewp_outputs[f'{remote_ki["output"]}{remote_ki['workplan']}'], )

        local_ewp_kis.update(new_kis)
        self.ewp_key_interventions = local_ewp_kis
        return total_data, total_updated, len(new_kis)

    def update_activities(self):
        rem_activities = self.data['activities']
        activity_type = ResultType.objects.get(name=ResultType.ACTIVITY)
        total_data = len(rem_activities)
        total_updated = 0

        loc_activities = dict([(r.wbs, r) for r in Result.objects.filter(wbs__in=list(rem_activities.keys()),
                                                                         result_type__name=ResultType.ACTIVITY)])

        for loc_activity in loc_activities.values():
            if self._update_changes(loc_activity, rem_activities[loc_activity.wbs]):
                logger.debug('Updated {}'.format(loc_activity))
                loc_activity.save()
                total_updated += 1
            del rem_activities[loc_activity.wbs]

        new_activities = {}
        for rem_activity in rem_activities.values():
            rem_activity['country_programme'] = self._get_local_parent(rem_activity['wbs'], 'cp')
            rem_activity['parent'] = self._get_local_parent(rem_activity['wbs'], 'output')
            rem_activity['result_type'] = activity_type

            new_activities[rem_activity['wbs']], _ = Result.objects.get_or_create(**rem_activity)

        # add the newly created cps
        loc_activities.update(new_activities)
        self.outputs = loc_activities
        return total_data, total_updated, len(new_activities)

    @transaction.atomic
    def update(self):
        # data
        # {"remote_cps": country_programmes_wbss,
        #  "remote_outputs": output_wbss,
        #  "remote_kis": ki_wbss,
        #  "remote_partners": partner_vendor_numbers,
        #  "remote_locations": location_p_codes,
        #  "remote_ewps": ewps,
        #  "activities": activities}


        total_ewps = self.update_workplans()
        ewps = 'CPs updated: Total {}, Updated {}, New {}'.format(*total_ewps)

        # update / add new Outcomes
        total_outputs = self.update_ewp_outputs()
        outputs = 'eWorkplans updated: Total {}, Updated {}, New {}'.format(*total_outputs)

        # update / add new Outputs
        total_kis = self.update_kis()
        kis = 'KIs updated: Total {}, Updated {}, New {}'.format(*total_kis)

        # update / add new Activities
        # total_activities = self.update_activities()
        # activities = 'Activities updated: Total {}, Updated {}, New {}'.format(*total_activities)

        return {
            'details': '\n'.join([ewps, outputs, kis]),
            'total_records': sum([i[0] for i in [total_ewps, total_outputs, total_kis]]),
            'processed': sum([i[1] + i[2] for i in [total_ewps, total_outputs, total_kis]])
        }


class EWPsSynchronizer(FileDataSynchronizer):
    # ENDPOINT = 'ramworkplans'
    # REQUIRED_KEYS = (
    #     "COUNTRY_PROGRAMME_NAME",
    #     "COUNTRY_PROGRAMME_WBS",
    #     "CP_START_DATE",
    #     "CP_END_DATE",
    #     "GOAL_AREA_CODE",
    #     "GOAL_AREA_NAME",
    #     "OUTCOME_WBS",
    #     "OUTCOME_NAME",
    #     "OUTCOME_START_DATE",
    #     "OUTCOME_END_DATE",
    #     "OUTPUT_WBS",
    #     "OUTPUT_NAME",
    #     "OUTPUT_START_DATE",
    #     "OUTPUT_END_DATE",
    #     "ACTIVITY_WBS",
    #     "ACTIVITY_NAME",
    #     "ACTIVITY_START_DATE",
    #     "ACTIVITY_END_DATE",
    #     "SIC_CODE",
    #     "SIC_NAME",
    #     "GIC_CODE",
    #     "GIC_NAME",
    #     "ACTIVITY_FOCUS_CODE",
    #     "ACTIVITY_FOCUS_NAME",
    #     "GENDER_MARKER_CODE",
    #     "GENDER_MARKER_NAME",
    #     "HUMANITARIAN_TAG",
    #     "HUMANITARIAN_MARKER_CODE",
    #     "HUMANITARIAN_MARKER_NAME",
    #     "RESULT_AREA_CODE",
    #     "RESULT_AREA_NAME",
    # )
    DATES = (
        "WPA_END_DATE",
        "WPA_START_DATE",
    )
    EWP_MAP = (
        ("WP_ID", "ewp_id"),
        ("WP_GID", "wbs"),
        ("WP_NAME", "name"),
        ("WP_STATUS", "status"),
        ("COST_CENTER_CODE", "cost_center_code"),
        ("COST_CENTER_NAME", "cost_center_name"),
        ("PLAN_CATEGORY_TYPE", "category_type"),
        ("PLAN_TYPE", "plan_type"),
        ("CP_WBS", "country_programme"),
    )
    ACTIVITY_MAP = (
        ("WPA_GID", "wpa_wbs"),
        ("WPA_ID", "wpa_id"),
        # ("WPA_START_DATE", "start_date"),
        # ("WPA_END_DATE", "end_date"),
        ("WPA_TITLE", "title"),
        ("WPA_DESCRIPTION", "description"),
        ("TOTAL_BUDGET", "total_budget"),
        ("WPA_GEOLOCATIONS", "locations"),
        ("WPA_IMPLEMENTING_PARTNERS", "partners"),
    )
    REQUIRED_KEYS = set([r[0] for r in list(EWP_MAP + ACTIVITY_MAP)])

    def _filter_by_time_range(self, records):
        records = super()._filter_records(records)

        today = datetime.datetime.today()
        last_year = datetime.datetime(today.year - 1, 1, 1).date()

        def in_time_range(record):
            if not record['OUTCOME_END_DATE'] or record['OUTCOME_END_DATE'] >= last_year:
                return True
            return False

        return [record for record in records if in_time_range(record)]

    def _clean_records(self, records):
        # records = self._filter_by_time_range(records)
        country_programmes_wbss = set()

        ki_wbss = []
        ki_wbss_seen = set()
        output_wbss = []
        output_wbss_seen = set()

        partner_vendor_numbers = set()
        location_p_codes = set()
        ewps = {}
        activities = {}
        for r in records:
            country_programmes_wbss.add(r['CP_WBS'])

            output_key = (r['VISION_ACTIVITY_WBS'][:18], r['WP_GID'])
            if output_key not in output_wbss_seen:
                output_wbss.append({"wbs": output_key[0], "workplan": output_key[1]})
                output_wbss_seen.add(output_key)

            # Adding unique `ki_wbss`
            ki_key = (r['VISION_ACTIVITY_WBS'], r['VISION_ACTIVITY_WBS'][:18], r['WP_GID'])
            if ki_key not in ki_wbss_seen:
                ki_wbss.append({"wbs": ki_key[0], "output": ki_key[1], "workplan": ki_key[2]})
                ki_wbss_seen.add(ki_key)

            if not ewps.get(r['WP_GID'], None):
                if all([r[i[0]] for i in self.EWP_MAP]):
                    ewps[r['WP_GID']] = dict([(i[1], r[i[0]]) for i in self.EWP_MAP])


            if not activities.get(r['VISION_ACTIVITY_WBS'], None):
                if all([r[i[0]] for i in self.ACTIVITY_MAP]):
                    result = {}
                    for item in self.ACTIVITY_MAP:
                        remote_key = item[0]
                        local_prop = item[1]
                        if local_prop == 'locations' and isinstance(r[remote_key], dict):
                            if r[remote_key].get('GEOLOCATION', None):
                                loc_list = r[remote_key]['GEOLOCATION']
                                if loc_list and isinstance(loc_list, list):
                                    result[local_prop] = [loc['P_CODE'] for loc in loc_list]
                                    location_p_codes.update(result[local_prop])
                        elif local_prop == 'partners':
                            if isinstance(r[remote_key], dict) and r[remote_key].get('IMPL_PARTNER', None):
                                remote_partners = r[remote_key]['IMPL_PARTNER']
                                if remote_partners and isinstance(remote_partners, list):
                                    result[local_prop] = [p['IMPLEMENTING_PARTNER_CODE'] for p in remote_partners]
                                    partner_vendor_numbers.update(result[local_prop])
                        else:
                            result[local_prop] = r[remote_key]

                    activities[r['VISION_ACTIVITY_WBS']] = result

        return {"remote_cps": country_programmes_wbss,
                "remote_outputs": output_wbss,
                "remote_kis": ki_wbss,
                "remote_partners": partner_vendor_numbers,
                "remote_locations": location_p_codes,
                "remote_ewps": ewps,
                "activities": activities}

    def _convert_records(self, records):
        # try:
        #     records = records['ROWSET']['ROW']
        # except KeyError as exc:
        #     raise VisionException(f'Expected key {exc} is missing from API response {records}.')

        # with open('vision_response.json', 'w') as file:
        #     json.dump(records, file, indent=4)

        for r in records:
            for k in self.DATES:
                r[k] = datetime.datetime.strptime(r[k], INSIGHT_DATE_FORMAT).date() if r[k] else None
            r['PLAN_AT_KI_LEVEL'] = r['PLAN_AT_KI_LEVEL'] not in ['No', 'None', '0']

        return self._clean_records(records)


    def _save_records(self, records):
        # synchronizer = ResultStructureSynchronizer(records)
        synchronizer = EWPSynchronizer(records)
        return synchronizer.update()

        # return synchronizer.update()


