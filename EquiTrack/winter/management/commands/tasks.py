__author__ = 'jcranwellward'

import os
import json
import requests

from requests.auth import HTTPBasicAuth
from django.contrib.auth.models import Group

from pymongo import MongoClient
from cartodb import CartoDBAPIKey, CartoDBException


def set_docs(docs):

    user_json = json.dumps(
        {
            'docs': docs,
            'all_or_nothing': True
        }

    )
    reponse = requests.post(
        'http://cb.uniceflebanon.org:4984/unisupply/_bulk_docs',
        headers={'content-type': 'application/json'},
        # auth=HTTPBasicAuth('unisupply-gateway', 'W!nT3er!zAtioN'),
        data=user_json,
    )
    print reponse


def set_users():

    user_docs = []
    groups = Group.objects.filter(name__icontains='winter')
    users = [user for group in groups for user in group.user_set.all()]
    for user in users:
        user_docs.append(
            {
                "type": "user",
                "username": user.username,
                "password": user.last_name,
                "organisation": user.username,
                "roles": [group.name.split("_")[1] for group in user.groups.all()]
            }
        )

    set_docs(user_docs)


def set_sites(
        api_key='12d24a4f231dc516f83a3045ce133ab2977ee77e',
        domain='equitrack',
        table_name='winterazation_master_list_v8_zn',
        site_type='IS',
        name_col='pcodename',
        code_col='p_code',
    ):

    client = CartoDBAPIKey(api_key, domain)

    sites = client.sql(
        'select * from {}'.format(table_name)
    )

    locations = []
    for row in sites['rows']:

        location = {
            "_id": row[code_col],
            "type": "location",
            "site-type": site_type,
            "p_code": row[code_col],
            "p_code_name": row[name_col].encode('UTF-8'),
            "longitude": row['long'],
            "latitude": row['lat']
        }
        locations.append(location)

    set_docs(locations)


def import_docs(
        url='http://cb.uniceflebanon.org:4984',
        bucket='unisupply',
        query='_all_docs?include_docs=true'):
    """
    Imports docs from couch base
    """

    data = requests.get('{url}/{bucket}/{query}'.format(
        url=url,
        bucket=bucket,
        query=query
    )).json()

    mongo = MongoClient(
        os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))[
        os.environ.get('MONGODB_DATABASE', 'winter')]

    for row in data['rows']:
        doc = row['doc']
        mongo.winter.update({'_id': doc['_id']}, doc, upsert=True)

