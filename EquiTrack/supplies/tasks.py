__author__ = 'jcranwellward'

import os
import json
import requests
import datetime

from django.conf import settings
from django.template.defaultfilters import slugify

from requests.auth import HTTPBasicAuth

from pymongo import MongoClient

from EquiTrack.celery import app






@app.task
def send(message):
    if settings.SLACK_URL:
        requests.post(
            settings.SLACK_URL,
            data=json.dumps({'text': message})
        )


def set_docs(docs):

    payload_json = json.dumps(
        {
            'docs': docs,
            'all_or_nothing': True
        }
    )
    response = requests.post(
        os.path.join(settings.COUCHBASE_URL, '_bulk_docs'),
        headers={'content-type': 'application/json'},
        auth=HTTPBasicAuth(settings.COUCHBASE_USER, settings.COUCHBASE_PASS),
        data=payload_json,
    )
    return response


def set_unisupply_user(username, password):

    user_docs = []
    user_docs.append(
        {
            "_id": username,
            "type": "user",
            "username": username,
            "password": password,
            "organisation": username,
        }
    )

    set_docs.delay(user_docs)


@app.task
def set_unisupply_distribution(distribution_plan):

        response = set_docs([
            {
                "_id": slugify("{} {} {} {}".format(
                    distribution_plan.partnership,
                    distribution_plan.item,
                    distribution_plan.location,
                    distribution_plan.quantity
                )),
                "partner_name": distribution_plan.partnership.partner.name,
                "assessment_type": "institution",
                "criticality": "0",
                "item_list": [
                    {
                        "item_id": "SB001",
                        "item_type": distribution_plan.item.name,
                        "quantity": distribution_plan.quantity
                    }
                ],
                "location": {
                    "location_type": distribution_plan.location.gateway.name,
                    "p_code": distribution_plan.location.p_code,
                    "p_code_name": distribution_plan.location.name,
                },
                "type": "assessment",
                "completed": False,
                "creation_date": datetime.datetime.now().isoformat(),
                "name": "N/A",
            }
        ])
        if response.status_code in [requests.codes.ok, requests.codes.created]:
            distribution_plan.send = False
            distribution_plan.sent = True
            distribution_plan.save()

        return response.text


@app.task
def import_docs(**kwargs):

        data = requests.get(
            os.path.join(settings.COUCHBASE_URL,'_all_docs?include_docs=true'),
            auth=HTTPBasicAuth(settings.COUCHBASE_USER, settings.COUCHBASE_PASS)
        ).json()

        rows = data['rows']

        connection = initiate_mongo_connection()
        db = connection.winter
        lebanon = db.data
        for row in rows:
             doc = row['doc']
            ## CHANGE IDIOT PARTNERS
             if ('partner_name' in doc.keys()):
                 if doc['partner_name'] == 'user5':
                     doc['partner_name'] = 'sawa'
                 if doc['partner_name'] == 'unicef-leb':
                     doc['partner_name'] = 'lost'


            ## REMOVE ARRAYS
             if ('type' in doc.keys()) and (doc['type'] == 'assessment') and (doc['id_type'] == 'UNHCR'):

                CSCSurvey = {}
                WFPSurvey = {}

                if 'surveys' in doc.keys():
                    for survey in doc['surveys']:

                        if survey.keys()[0] == "CSC Survey":
                            for question in survey['CSC Survey']:
                                CSCSurvey.update(question)
                        elif survey.keys()[0] == "WFP Survey":
                            for question in survey['WFP Survey']:
                                WFPSurvey.update(question)


                doc['surveys']={"CSC Survey":CSCSurvey}
                doc['surveys'].update({"WFP Survey": WFPSurvey})

             lebanon.update({'_id': doc['_id']}, doc, upsert=True)





def initiate_mongo_connection():
    connection = MongoClient(host='localhost',port=27017)
    db = connection.winter
    return db.data

def crunch_winter_data(**kwargs):
    data = initiate_mongo_connection()
    cursor = data.aggregate([
        {'$match': {'type': 'assessment'}},
        {'$unwind': '$child_list'},
        {'$project':
            {
                'p_code': '$location.p_code',
                'p_code_name': '$location.p_code_name',
                'latitude': '$location.latitude',
                'longitude': '$location.longitude',
                'phone_number': 1,
                'first_name': 1,
                'middle_name': 1,
                'family_name': 1,
                'official_id': 1,
                'id_type': 1,
                'gender': 1,
                'marital_status': 1,
                'creation_date': 1,
                'partner_name': 1,
                'answer1': 1,
                'answer2': 1,
                'answer3': 1,
                'answer4': 1,
                'new_location': 1,
                'Under 4 months': {"$cond": [{"$eq": ["$child_list.age", "Under 4 months"]}, 1, 0]},
                'Under 24 months': {"$cond": [{"$eq": ["$child_list.age", "Under 24 months"]}, 1, 0]},
                '2 years': {"$cond": [{"$eq": ["$child_list.age", "2 years"]}, 1, 0]},
                '3 years': {"$cond": [{"$eq": ["$child_list.age", "3 years"]}, 1, 0]},
                '4 years': {"$cond": [{"$eq": ["$child_list.age", "4 years"]}, 1, 0]},
                '5 years': {"$cond": [{"$eq": ["$child_list.age", "5 years"]}, 1, 0]},
                '6 years': {"$cond": [{"$eq": ["$child_list.age", "6 years"]}, 1, 0]},
                '7 years': {"$cond": [{"$eq": ["$child_list.age", "7 years"]}, 1, 0]},
                '8 years': {"$cond": [{"$eq": ["$child_list.age", "8 years"]}, 1, 0]},
                '9 years': {"$cond": [{"$eq": ["$child_list.age", "9 years"]}, 1, 0]},
                '10 years': {"$cond": [{"$eq": ["$child_list.age", "10 years"]}, 1, 0]},
                '11 years': {"$cond": [{"$eq": ["$child_list.age", "11 years"]}, 1, 0]},
                '12 years': {"$cond": [{"$eq": ["$child_list.age", "12 years"]}, 1, 0]},
                '13 years': {"$cond": [{"$eq": ["$child_list.age", "13 years"]}, 1, 0]},
                '14 years': {"$cond": [{"$eq": ["$child_list.age", "14 years"]}, 1, 0]},

                'CSC Survey Q1': "$surveys.CSC Survey.Q1.answer",
                'CSC Survey Q2': "$surveys.CSC Survey.Q2.answer",
                'CSC Survey Q3': "$surveys.CSC Survey.Q3.answer",
                'CSC Survey Q4': "$surveys.CSC Survey.Q4.answer",
                'CSC Survey Q5': "$surveys.CSC Survey.Q5.answer",
                'CSC Survey Q6': "$surveys.CSC Survey.Q6.answer",
                'CSC Survey Q7': "$surveys.CSC Survey.Q7.answer",
                'CSC Survey Q8': "$surveys.CSC Survey.Q8.answer",
                'CSC Survey Q9': "$surveys.CSC Survey.Q9.answer",
                'CSC Survey Q10': "$surveys.CSC Survey.Q10.answer",

                'WFP Survey Q1': "$surveys.WFP Survey.Q1.answer",
                'WFP Survey Q2': "$surveys.WFP Survey.Q2.answer",
                'WFP Survey Q3': "$surveys.WFP Survey.Q3.answer",
                'WFP Survey Q4': "$surveys.WFP Survey.Q4.answer",
                'WFP Survey Q5': "$surveys.WFP Survey.Q5.answer",
                'WFP Survey Q6': "$surveys.WFP Survey.Q6.answer",
                'WFP Survey Q7': "$surveys.WFP Survey.Q7.answer",
                'WFP Survey Q8': "$surveys.WFP Survey.Q8.answer",
                'WFP Survey Q9': "$surveys.WFP Survey.Q9.answer",
                'WFP Survey Q10': "$surveys.WFP Survey.Q10.answer",
                'WFP Survey Q11': "$surveys.WFP Survey.Q11.answer",

            }
        },

        {'$group':
            {
                '_id': "$official_id",
                'p_code': {'$first': '$p_code'},
                'p_code_name': {'$first': '$p_code_name'},
                'phone_number': {'$first': '$phone_number'},
                'latitude': {'$first': '$latitude'},
                'longitude': {'$first': '$longitude'},
                'first_name': {'$first': '$first_name'},
                'middle_name': {'$first': '$middle_name'},
                'last_name': {'$first': '$family_name'},
                'official_id': {'$first': '$official_id'},
                'id_type': {'$first': '$id_type'},
                'gender': {'$first': '$gender'},
                'marital_status': {'$first': '$marital_status'},
                'creation_date': {'$first': '$creation_date'},
                'partner_name': {'$first': '$partner_name'},
                'Do you have school-aged children not attending school?': {'$first': '$answer1'},
                'Do you have school aged children working': {'$first': '$answer2'},
                'Is the principle applicant still present?': {'$first': '$answer3'},
                'Will the family move in the near future?': {'$first': '$answer4'},
                'new_location': {'$first': '$new_location'},
                'Under 4 months': {'$sum': "$Under 4 months"},
                'Under 24 months': {'$sum': "$Under 24 months"},
                '2 years': {'$sum': "$2 years"},
                '3 years': {'$sum': "$3 years"},
                '4 years': {'$sum': "$4 years"},
                '5 years': {'$sum': "$5 years"},
                '6 years': {'$sum': "$6 years"},
                '7 years': {'$sum': "$7 years"},
                '8 years': {'$sum': "$8 years"},
                '9 years': {'$sum': "$9 years"},
                '10 years': {'$sum': "$10 years"},
                '11 years': {'$sum': "$11 years"},
                '12 years': {'$sum': "$12 years"},
                '13 years': {'$sum': "$13 years"},
                '14 years': {'$sum': "$14 years"},
                'CSC Survey Q1 - Did you recieve the CSC card?': {'$last': '$CSC Survey Q1'},
                'CSC Survey Q2 - Do you still have the CSC card?': {'$last': '$CSC Survey Q2'},
                'CSC Survey Q3 - Do you remember the PIN number?': {'$last': '$CSC Survey Q3'},
                'CSC Survey Q4 - Please enter the last four digits of the card': {'$last': '$CSC Survey Q4'},
                'CSC Survey Q5 - Is the case number written on the card equal to the one in the registration certificate?': {
                    '$last': '$CSC Survey Q5'},
                'CSC Survey Q6 - Reasons for not having the card': {'$last': '$CSC Survey Q6'},
                'CSC Survey Q7 - Did you inform UNHCR or the Bank?': {'$last': '$CSC Survey Q7'},
                'CSC Survey Q8 - Did UNHCR issue a new PIN number?': {'$last': '$CSC Survey Q8'},
                'CSC Survey Q9 - Input number of actual card:': {'$last': '$CSC Survey Q9'},
                'CSC Survey Q10 - Did you inform UNHCR or the Bank?': {'$last': '$CSC Survey Q10'},

                'WFP Survey Q1 - Did you recieve a WFP Food voucher card?': {'$last': '$WFP Survey Q1'},
                'WFP Survey Q2 - Do you still have the WFP voucher card?': {'$last': '$WFP Survey Q2'},
                'WFP Survey Q3 - Please input the last 4 digits of the WFP card:': {'$last': '$WFP Survey Q3'},
                'WFP Survey Q4 - Does the case number correspond to the WFP card?': {'$last': '$WFP Survey Q4'},
                'WFP Survey Q5 - Did your WFP voucher Card get upgraded to an ATM Card?': {'$last': '$WFP Survey Q5'},
                'WFP Survey Q6 - Do you still have the PIN number?': {'$last': '$WFP Survey Q6'},
                'WFP Survey Q7 - Is the card still functioning/activated?': {'$last': '$WFP Survey Q7'},
                'WFP Survey Q8 - Reasons for not having the WFP card': {'$last': '$WFP Survey Q8'},
                'WFP Survey Q9 - Did you notify the partner/bank?': {'$last': '$WFP Survey Q9'},
                'WFP Survey Q10 - Take down the card number:': {'$last': '$WFP Survey Q10'},
                'WFP Survey Q11 - Did you inform the bank?': {'$last': '$WFP Survey Q11'},

            }
        }
    ])
    return cursor


