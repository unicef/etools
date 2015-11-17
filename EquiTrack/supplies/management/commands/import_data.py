__author__ = 'Tarek'


import os
import json
import requests
import datetime

from django.conf import settings
from pymongo import MongoClient
from django.template.defaultfilters import slugify

from requests.auth import HTTPBasicAuth
from django.core.management.base import BaseCommand


class Command(BaseCommand):

    can_import_settings = True

    def handle(self, **options):

        data = requests.get(
            os.path.join(settings.COUCHBASE_URL,'_all_docs?include_docs=true'),
            auth=HTTPBasicAuth(settings.COUCHBASE_USER, settings.COUCHBASE_PASS)
        ).json()

        rows = data['rows']

        connection = MongoClient()
        db = connection.winter
        lebanon = db.data
        for row in rows:
             doc = row['doc']

             if ('partner_name' in doc.keys()):
                 if doc['partner_name'] == 'user5':
                     doc['partner_name'] = 'Sawa'
                 if doc['partner_name'] == 'unicef-leb':
                     doc['partner_name'] = 'Lost'

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