import datetime
import logging

from django.db import transaction
from django.db.models import Q

from unicef_vision.exceptions import VisionException
from unicef_vision.settings import INSIGHT_DATE_FORMAT

from etools.applications.environment.helpers import tenant_switch_is_active
from etools.applications.governments.models import EWPActivity, EWPKeyIntervention, EWPOutput, GovernmentEWP
from etools.applications.locations.models import Location
from etools.applications.partners.models import PartnerOrganization
from etools.applications.reports.models import CountryProgramme, Result, ResultType
from etools.applications.vision.synchronizers import VisionDataTenantSynchronizer

logger = logging.getLogger(__name__)


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
        missing_cps = set(self.data['remote_cps']) - self.cps.keys()
        if missing_cps:
            logger.warning(f"Missing CountryProgrammes for WBSs: {missing_cps}")
            self.data['remote_cps'] = [wbs for wbs in self.data['remote_cps'] if wbs not in missing_cps]

        self.outputs = {r.wbs: r for r in
                        Result.objects.filter(wbs__in=[r["wbs"] for r in self.data['remote_outputs']],
                                              result_type__name=ResultType.OUTPUT)}
        remote_output_wbss = {r["wbs"] for r in self.data['remote_outputs']}
        missing_outputs = remote_output_wbss - self.outputs.keys()
        if missing_outputs:
            logger.warning(f"Missing Outputs for WBSs: {missing_outputs}")
            self.data['remote_outputs'] = [
                r for r in self.data['remote_outputs'] if r["wbs"] not in missing_outputs
            ]

        self.kis = {r.wbs: r for r in
                    Result.objects.filter(wbs__in=[r["wbs"] for r in self.data['remote_kis']],
                                          result_type__name=ResultType.ACTIVITY)}

        remote_ki_wbss = {r["wbs"] for r in self.data['remote_kis']}
        missing_kis = remote_ki_wbss - self.kis.keys()
        if missing_kis:
            logger.warning(f"Missing KIs for WBSs: {missing_kis}")
            self.data['remote_kis'] = [
                r for r in self.data['remote_kis'] if r["wbs"] not in missing_kis
            ]

        self.locations = {r.p_code: r for r in Location.objects.filter(p_code__in=self.data['remote_locations'])}
        missing_locations = set(self.data['remote_locations']) - self.locations.keys()
        if missing_locations:
            logger.warning(f"Missing Locations for P-Codes: {missing_locations}")
            self.data['remote_locations'] = [
                p_code for p_code in self.data['remote_locations'] if p_code not in missing_locations
            ]

        self.partners = {r.organization.vendor_number: r for r in PartnerOrganization.objects.filter(
            organization__vendor_number__in=self.data['remote_partners'])}
        missing_partners = set(self.data['remote_partners']) - self.partners.keys()
        if missing_partners:
            logger.warning(f"Missing Partners for Vendor Numbers: {missing_partners}")
            self.data['remote_partners'] = [
                vendor_number for vendor_number in self.data['remote_partners'] if vendor_number not in missing_partners
            ]

    @staticmethod
    def _update_changes(local, remote):
        updated = False
        for k in remote:
            if k == "country_programme":
                pass
            elif getattr(local, k) != remote[k]:
                updated = True
                setattr(local, k, remote[k])

        return updated

    def _update_activity_changes(self, local, remote):
        updated = False
        for k in remote:
            match k:  # noqa: E999
                case 'workplan':

                    local_wp = self.workplans.get(remote[k])
                    if local_wp != local.workplan:
                        local.workplan = local_wp
                        updated = True

                case 'ewp_key_intervention':
                    # TODO: assuming certain things can't change like moving activities
                    pass

                case 'locations':
                    local_pcodes = [l.p_code for l in local.locations.all()]
                    if set(local_pcodes) != set(remote[k]):
                        new_locs = Location.objects.filter(p_code__in=set(remote[k]))
                        local.locations.set(new_locs)
                        updated = True

                case 'partners':
                    local_vendors = [p.organization.vendor_number for p in local.partners.all()]
                    if set(local_vendors) != set(remote[k]):
                        new_partners = PartnerOrganization.objects.filter(
                            organization__vendor_number__in=set(remote[k])
                        )
                        local.partners.set(new_partners)
                        updated = True

                case _:
                    if getattr(local, k) != remote[k]:
                        setattr(local, k, remote[k])
                        updated = True
        return updated

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

        local_ewp_outputs = {f'{record.cp_output.wbs}{record.workplan.wbs}': record for record in
                             EWPOutput.objects.filter(query)}

        new_remote_outputs = [item for item in remote_ewp_outputs if item["wbs"] not in local_ewp_outputs.keys()]

        new_outputs = {}
        for remote_output in new_remote_outputs:
            new_outputs[f'{remote_output["wbs"]}{remote_output["workplan"]}'], _ = EWPOutput.objects.get_or_create(
                cp_output=self.outputs[remote_output['wbs']], workplan=self.workplans[remote_output['workplan']], )

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

        local_ewp_kis = {
            f'{record.cp_key_intervention.wbs}{record.ewp_output.workplan.wbs}': record for record in EWPKeyIntervention.objects.filter(query)}

        new_remote_kis = [item for item in remote_ewp_kis if item["wbs"] not in local_ewp_kis.keys()]

        new_kis = {}
        for remote_ki in new_remote_kis:
            new_kis[f'{remote_ki["wbs"]}{remote_ki["workplan"]}'], _ = EWPKeyIntervention.objects.get_or_create(
                cp_key_intervention=self.kis[remote_ki['wbs']],
                ewp_output=self.ewp_outputs[f'{remote_ki["output"]}{remote_ki["workplan"]}'], )

        local_ewp_kis.update(new_kis)
        self.ewp_key_interventions = local_ewp_kis
        return total_data, total_updated, len(new_kis)

    def update_activities(self):
        rem_activities = self.data['activities']
        total_data = len(rem_activities)
        total_updated = 0

        # TODO: Prefetch related...
        local_activities = {record.wbs: record for record in
                            EWPActivity.objects.filter(wbs__in=list(rem_activities.keys()))}
        for local_act in local_activities.values():
            if self._update_activity_changes(local_act, rem_activities[local_act.wbs]):
                logger.debug('Updated {}'.format(local_act))
                total_updated += 1
                local_act.save()
            del rem_activities[local_act.wbs]

        # Todo bulk save:
        new_activities = {}
        for remote_activity in rem_activities.values():
            ewp_ki_key = f'{remote_activity["ewp_key_intervention"]}{remote_activity["workplan"]}'
            # if there are no workplans or key interventions to match it means that we were missing some records like
            # certain CP Key Interventions (or activities) as not present in Insight Results Sync
            try:
                remote_activity['workplan'] = self.workplans[remote_activity['workplan']]
                remote_activity['ewp_key_intervention'] = self.ewp_key_interventions[ewp_ki_key]
            except KeyError:
                continue
            vendor_numbers = remote_activity.pop('partners', [])
            p_codes = remote_activity.pop('locations', [])
            new_activities[remote_activity['wbs']], _ = EWPActivity.objects.get_or_create(**remote_activity)

            new_activities[remote_activity['wbs']].partners.set(
                [self.partners.get(v) for v in vendor_numbers if self.partners.get(v) is not None]
            )
            new_activities[remote_activity['wbs']].locations.set(
                [self.locations.get(v) for v in p_codes if self.locations.get(v) is not None]
            )

        # add the newly created cps
        local_activities.update(new_activities)
        self.activities = local_activities

        return total_data, total_updated, len(new_activities)

    @transaction.atomic
    def update(self):
        total_ewps = self.update_workplans()
        ewps = 'CPs updated: Total {}, Updated {}, New {}'.format(*total_ewps)

        # update / add new Outcomes
        total_outputs = self.update_ewp_outputs()
        outputs = 'eWorkplans updated: Total {}, Updated {}, New {}'.format(*total_outputs)

        # update / add new Outputs
        total_kis = self.update_kis()
        kis = 'KIs updated: Total {}, Updated {}, New {}'.format(*total_kis)

        # update / add new Activities
        total_activities = self.update_activities()
        activities = 'Activities updated: Total {}, Updated {}, New {}'.format(*total_activities)

        return {
            'details': '\n'.join([ewps, outputs, kis, activities]),
            'total_records': sum([i[0] for i in [total_ewps, total_outputs, total_kis, total_activities]]),
            'processed': sum([i[1] + i[2] for i in [total_ewps, total_outputs, total_kis, total_activities]])
        }


# class EWPsSynchronizer(FileDataSynchronizer):
class EWPsSynchronizer(VisionDataTenantSynchronizer):
    ENDPOINT = 'ramworkplans'
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
        ("WPA_GID", "wbs"),
        ("WPA_ID", "wpa_id"),
        ("WPA_START_DATE", "start_date"),
        ("WPA_END_DATE", "end_date"),
        ("WPA_TITLE", "title"),
        ("WPA_DESCRIPTION", "description"),
        ("TOTAL_BUDGET", "total_budget"),
        ("WPA_GEOLOCATIONS", "locations"),
        ("WPA_IMPLEMENTING_PARTNERS", "partners"),
        ("VISION_ACTIVITY_WBS", "ewp_key_intervention"),
        ('WP_GID', "workplan"),  # This is the WBS, map later
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
            skip = False
            for i in self.ACTIVITY_MAP:
                if not r.get(i[0]) and i[0] not in ['TOTAL_BUDGET', 'WPA_GEOLOCATIONS', 'WPA_IMPLEMENTING_PARTNERS', 'WPA_DESCRIPTION']:
                    logger.warning(f"Skipping: Missing {i[0]} for record: {r.get('VISION_ACTIVITY_WBS', 'UNKNOWN')}")
                    skip = True
            if skip:
                continue

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

            if not activities.get(r['WPA_GID'], None):
                result = {}
                for item in self.ACTIVITY_MAP:
                    remote_key = item[0]
                    local_prop = item[1]

                    if local_prop == 'locations':
                        geo_data = r.get(remote_key)
                        if not geo_data:
                            # if no locations were provided, set the default to the country location
                            country_location = Location.objects.active().filter(admin_level=0).first()
                            result[local_prop] = [country_location.p_code]
                        elif isinstance(geo_data, dict):
                            if 'GEOLOCATION' in geo_data:
                                locs = geo_data['GEOLOCATION']
                                if locs:
                                    if isinstance(locs, list):
                                        result[local_prop] = [loc['P_CODE'] for loc in locs]
                                    elif isinstance(locs, dict):
                                        result[local_prop] = [locs['P_CODE']]

                        location_p_codes.update(result[local_prop])

                    elif local_prop == 'partners':
                        # this allows future syncs in case partners are missing due to upstream delays.
                        result[local_prop] = []
                        partners_data = r.get(remote_key)
                        if isinstance(partners_data, dict) and partners_data.get('IMPL_PARTNER', None):
                            remote_partners = partners_data['IMPL_PARTNER']
                            if remote_partners:
                                if isinstance(remote_partners, list):
                                    result[local_prop] = [p['IMPLEMENTING_PARTNER_CODE'] for p in remote_partners]
                                elif isinstance(remote_partners, dict):
                                    result[local_prop] = [remote_partners['IMPLEMENTING_PARTNER_CODE']]
                                partner_vendor_numbers.update(result[local_prop])
                    else:
                        result[local_prop] = r.get(remote_key)

                    activities[r['WPA_GID']] = result

        return {"remote_cps": country_programmes_wbss,
                "remote_outputs": output_wbss,
                "remote_kis": ki_wbss,
                "remote_partners": partner_vendor_numbers,
                "remote_locations": location_p_codes,
                "remote_ewps": ewps,
                "activities": activities}

    def _convert_records(self, records):
        try:
            records = records['ROWSET']['ROW']
        except KeyError as exc:
            raise VisionException(f'Expected key {exc} is missing from API response {records}.')

        for r in records:
            for k in self.DATES:
                r[k] = datetime.datetime.strptime(r[k], INSIGHT_DATE_FORMAT).date() if r[k] else None
            r['PLAN_AT_KI_LEVEL'] = r['PLAN_AT_KI_LEVEL'] not in ['No', 'None', '0']

        return self._clean_records(records)

    def _save_records(self, records):
        synchronizer = EWPSynchronizer(records)
        return synchronizer.update()

    def sync(self):
        if tenant_switch_is_active("EWP Sync Disabled"):
            raise VisionException("EWP Sync is disabled")
        return super().sync()
