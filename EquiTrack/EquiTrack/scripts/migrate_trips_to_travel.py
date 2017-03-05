#!/usr/bin/env python

"""
python manage.py runscript migrate_trips_to_travel.py --traceback -v2
"""
import itertools
from collections import OrderedDict
from operator import attrgetter

from django.db import transaction
from django.db import IntegrityError
from django.db.transaction import TransactionManagementError
from django.core.exceptions import ObjectDoesNotExist

from users.models import Country

from EquiTrack.util_scripts import set_country

from trips.models import Trip
from t2f.models import Travel
from t2f.models import TravelActivity
from t2f.models import IteneraryItem
from t2f.models import CostAssignment
from t2f.models import ActionPoint
from t2f.models import TravelAttachment
from publics.models import Grant
from publics.models import WBS
from publics.models import BusinessArea
from publics.models import BusinessRegion
from partners.models import Intervention

TRIPTRAVEL_FIELDS_MAP = OrderedDict({
    "supervisor": "supervisor",
    "status": "status",
    "owner": "traveler",
    "section": "section",
    "office": "office",
    "purpose_of_travel": "purpose",
    "from_date": "start_date",
    "to_date": "end_date",
    "ta_required": "ta_required",
    "international_travel": "international_travel",
})

TRAVEL_TYPE_MAP = {
        'programme_monitoring': 'Programmatic Visit',
        'spot_check':'Spot Check',
        'advocacy': 'Advocacy',
        'technical_support': 'Technical Support',
        'meeting': 'Meeting',
        'duty_travel': 'Technical Support',
        'home_leave':'Staff Entitlement',
        'family_visit':'Staff Entitlement',
        'education_grant': 'Staff Entitlement',
        'staff_development': 'Staff Development',
        'staff_entitlement': 'Staff Entitlement',
}


biz_region = BusinessRegion(name='bizness', code='TK')
biz_region.save()

def migrate_trips(country):
    set_country(country.name)
    trips = Trip.objects.all()
    failed_travel_attachments = []
    trips_with_gov_activities = []
    failed_reference = []
    failed_integrity = []
    try:
        for trip in trips:
            print 'trip: ', trip.reference()

            travel_payload = dict(zip(TRIPTRAVEL_FIELDS_MAP.values(),
                                      attrgetter(*TRIPTRAVEL_FIELDS_MAP.keys())(trip)))

            # TODO check that this formatting isnt horrible
            # TODO check that these should be \n rather than <br/>
            report_note = '\n'.join(itertools.ifilter(lambda s: isinstance(s, basestring),
                                                      [trip.main_observations, trip.constraints,
                                                       trip.lessons_learned, trip.opportunities]))

            travel_payload.update({"report_note": report_note})
            ref_number = trip.reference().split('-')[0]
            if len(trip.reference()) < 6 or trip.reference()[4] != "/":
                print "record has bbad ref number {} : id: {}".format(trip.reference(), trip.id)
                continue
            travel_payload.update({"reference_number": ref_number})

            #print 'payload', travel_payload
            with transaction.atomic():
                try:
                    travel = Travel(**travel_payload)
                    travel.save()
                except IndexError as e:
                    print('failed to generate reference number..')
                    failed_reference.append(trip.id)
                    continue
                except IntegrityError as e:
                    print('duplicate reference number {}'.format(travel_payload['reference_number']))
                    print('payload')
                    failed_integrity.append(trip.id)
                    continue

            if travel.additional_note is not None:
                travel.additional_note = travel.additional_note + 'TA Reference: ' + trip.ta_reference
            else:
                travel.additional_note = 'TA Reference: ' + trip.ta_reference

            try:
                # if we have a duplicate reference number, ignore
                travel.save()
            except IntegrityError:
                print('duplicate reference number, using exisitng Travel obj...')
                travel = Travel.objects.get(reference_number=trip.ta_reference)

            # kidus talked to Lebanon chief of ops, who wanted this stuff
            # stashed in additional_notes..
            try:
                additional_notes = {
                    "Travel Focal Point": trip.travel_assistant.get_full_name() if trip.travel_assistant is not None else '',
                    "Security Clearance Required": trip.security_clearance_required if trip.security_clearance_required is not None else '',
                    "Budget Owner": trip.budget_owner.get_full_name() if trip.budget_owner is not None else '',
                    "Representative": trip.representative.get_full_name() if trip.representative is not None else '',
                    "Certified by Human Resources": trip.approved_by_human_resources if trip.approved_by_human_resources is not None else '',
                    "Approved by Supervisor": trip.approved_by_supervisor if trip.approved_by_supervisor is not None else '',
                    "Approved by Budget Owner": trip.approved_by_budget_owner if trip.approved_by_budget_owner is not None else '',
                    "Date Human Resources Approved": trip.date_human_resources_approved if trip.date_human_resources_approved is not None else '',
                    "Representative Approval": trip.representative_approval if trip.representative_approval is not None else '',
                    "Approved Date": trip.approved_date if trip.approved_date is not None else '',
                    "Driver": trip.driver.get_full_name() if trip.driver is not None else '',
                    "Transport Booked": trip.transport_booked if trip.transport_booked is not None else '',
                    "Security Granted": trip.security_granted if trip.security_granted is not None else '',
                    "TA drafted?": trip.ta_drafted if trip.ta_drafted is not None else '',
                    "TA Drafted Date": trip.ta_drafted_date if trip.ta_drafted_date is not None else '',
                    "TA Reference": trip.ta_reference if trip.ta_reference is not None else '',
                    "Vision Approver": trip.vision_approver.get_full_name() if trip.vision_approver is not None else '',
                }
            except ObjectDoesNotExist:
                additional_notes = {}

            lines = {label + ': ' + str(value) for label, value in additional_notes.items() if
                     str(value) not in ['', None]}
            if lines:
                blob = '\n'.join(lines)
                if travel.additional_note is not None:
                    travel.additional_note = travel.additional_note + blob
                else:
                    travel.additional_note = blob
                travel.save()

            for route in trip.travelroutes_set.all():
                # TODO do something with route.remarks?
                itinerary_payload = {
                    "travel": travel,
                    "origin": route.origin,
                    "destination": route.destination,
                    "departure_date": route.depart,
                    "arrival_date": route.arrive,
                }
                # TODO this goddamn model is misspelled
                itinerary_item = IteneraryItem(**itinerary_payload)
                itinerary_item.save()

            for funds in trip.tripfunds_set.all():
                with transaction.atomic():
                    try:
                        business_area = BusinessArea.objects.get(code=country.business_area_code)
                    except ObjectDoesNotExist:
                        # TODO using a fake `region` here. hopefully we'll find
                        # one in the `try` block above...
                        business_area = BusinessArea(code=country.business_area_code,
                                                     name=country.name,
                                                     region=biz_region)
                        business_area.save()

                    if not funds.wbs.wbs:
                        print "Skipping Fund {} since no wbs in result".format(funds.id)
                        continue

                    try:
                        # wbs.wbs? more like wtf.wtf
                        wbs = WBS.objects.get(name=funds.wbs.wbs)
                    except ObjectDoesNotExist:
                        try:
                            # TODO no idea if `name` would be the same...
                            # TODO or if this should just be `funds.grant`
                            grant = Grant.objects.get(name=funds.grant.name)
                        except ObjectDoesNotExist:
                            # TODO just making with `name`
                            grant = Grant(name=funds.grant.name)
                            grant.save()

                        wbs = WBS(name=funds.wbs.wbs,
                                  business_area=business_area)
                        wbs.save()
                        wbs.grants.add(grant)
                        wbs.save()

                        costassignment_payload = {
                            "travel": travel,
                            "wbs": wbs,
                            "grant": grant,
                            "share": funds.amount,
                        }
                        costassignment = CostAssignment(**costassignment_payload)
                        costassignment.save()

            for action in trip.actionpoint_set.all():
                with transaction.atomic():
                    actionpoint_payload = {
                        "travel": travel,
                        "description": action.description,
                        "due_date": action.due_date,
                        "person_responsible": action.person_responsible,
                        "actions_taken": action.actions_taken,
                        "follow_up": action.follow_up,
                        # TODO this can't be null, so using person_responsible
                        "assigned_by": action.person_responsible,
                    }

                    # 'closed' is now 'completed'
                    if action.status == 'closed':
                        actionpoint_payload.update({"status": "completed"})
                    else:
                        actionpoint_payload.update({"status": action.status})

                    actionpoint = ActionPoint(**actionpoint_payload)
                    actionpoint.save()

            for fileattachment in trip.files.all():
                with transaction.atomic():
                    travelattachment_payload = {
                        "travel": travel,
                        "type": fileattachment.type.name,
                        # TODO does caption make sense as name here?
                        "name": fileattachment.report.name[:100],
                        "file": fileattachment.report,
                    }
                    travelattachment = TravelAttachment(**travelattachment_payload)
                    try:
                        travelattachment.save()
                    except Exception as e:
                        #SOme weird data error remember this problem
                        failed_travel_attachments.append(travel.id)
                        print 'EXception saving travel attachment {}'.format(travelattachment_payload)
                        continue


            # create TravelActivity objects
            linkedpartners_gov = trip.linkedgovernmentpartner_set.all()
            linkedpartners = trip.linkedpartner_set.all()
            travel_type = TRAVEL_TYPE_MAP[trip.travel_type]
            activities = False
            with transaction.atomic():
                if linkedpartners_gov.exists():
                    partners = linkedpartners_gov
                    for linked_partner in partners:
                        activities = True
                        activity_payload = {
                            "travel_type": travel_type,
                            "primary_traveler": trip.owner,
                            "partner": linked_partner.partner,
                            # TODO using `trip.from_date` because why not
                            "date": trip.from_date,
                        }
                        travel_activity = TravelActivity(**activity_payload)
                        travel_activity.save()
                        travel_activity.travels.add(travel)
                        for triplocation in trip.triplocation_set.all():
                            if not triplocation.location:
                                continue
                            travel_activity.locations.add(triplocation.location)
                        travel_activity.save()

                    if trip.status in [trip.COMPLETED, trip.APPROVED]:
                        trips_with_gov_activities.append(trip.id)
                        print "!!!GOV_PA|{} Please address this trip as government partner could not be added to travel activity".format(trip.id)
                    print "Linked government partner not ported into T2F id: {}  Partners {} ".format(trip.id, linkedpartners_gov.all())

                if linkedpartners.exists():
                    partners = linkedpartners

                    for linked_partner in partners:
                        activities = True
                        try:
                            intervention = Intervention.objects.get(
                                number=linked_partner.intervention.number
                            )
                        except (AttributeError, Intervention.DoesNotExist):
                            intervention = None


                        activity_payload = {
                            "travel_type": travel_type,
                            "primary_traveler": trip.owner,
                            "partner": linked_partner.partner,
                            # TODO using `trip.from_date` because why not
                            "date": trip.from_date,
                        }

                        if intervention is not None:
                            activity_payload.update({"partnership": intervention})

                        travel_activity = TravelActivity(**activity_payload)
                        travel_activity.save()

                        travel_activity.travels.add(travel)

                        for triplocation in trip.triplocation_set.all():
                            if not triplocation.location:
                                continue
                            travel_activity.locations.add(triplocation.location)
                        travel_activity.save()
                # add at least one activity
                if not activities:
                    activity_payload = {
                        "travel_type": travel_type,
                        "primary_traveler": trip.owner,
                        # TODO using `trip.from_date` because why not
                        "date": trip.from_date,
                    }
                    travel_activity = TravelActivity(**activity_payload)
                    travel_activity.save()
                    travel_activity.travels.add(travel)
                    for triplocation in trip.triplocation_set.all():
                        if not triplocation.location:
                            continue
                        travel_activity.locations.add(triplocation.location)
                    travel_activity.save()

    except IntegrityError, e:
        print "BAM!: %s" % e
    print('#############################################################')
    print('failed reference', failed_reference)
    print('failed integrity', failed_integrity)
    print('gov act problems', trips_with_gov_activities)


def migrate_trips_all_countries():

    for country in Country.objects.all():
        if country.name in ["Global"]:
            continue

        print("Migrating trips for: '%s'" % country.name)
        migrate_trips(country.name)


def migrate_trips_for(country_name):

    country = Country.objects.get(name=country_name)

    print("Migrating trips for: '%s'" % country.name)
    migrate_trips(country)