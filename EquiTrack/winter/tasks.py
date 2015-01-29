__author__ = 'jcranwellward'

import os
import json
import requests
import unidecode
import dateutil.parser
from operator import itemgetter

from requests.auth import HTTPBasicAuth
from django.contrib.auth.models import Group

from pymongo import MongoClient
from cartodb import CartoDBAPIKey, CartoDBException

winter = MongoClient(
    os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))[
    os.environ.get('MONGODB_DATABASE', 'winter')]

client = CartoDBAPIKey(
    '12d24a4f231dc516f83a3045ce133ab2977ee77e',
    'equitrack'
)


def send(message):
    requests.post(
        'https://hooks.slack.com/services/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',
        data=json.dumps({'text': message})
    )


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


def get_sites(
    table_name='winterazation_master_list_v8_zn',
    site_type='IS',
    name_col='pcodename',
    code_col='p_code',
):

    sites = client.sql(
        'select * from {}'.format(table_name)
    )

    for row in sites['rows']:
        winter.sites.update({'_id': row[code_col]}, row, upsert=True)


def set_sites(
    site_type='IS',
    name_col='pcodename',
    code_col='p_code'
):
    locations = []
    for site in winter.sites.find():

        location = {
            "_id": site[code_col],
            "type": "location",
            "site-type": site_type,
            "p_code": site[code_col],
            "p_code_name": site[name_col].encode('UTF-8'),
            "longitude": site['long'],
            "latitude": site['lat']
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

    existing = winter.data.find({'type': 'assessment'}).count()
    for row in data['rows']:
        doc = row['doc']
        winter.data.update({'_id': doc['_id']}, doc, upsert=True)

    imported = winter.data.find({'type': 'assessment'}).count()
    completed = winter.data.find(
        {'$and': [
            {'completion_date': {'$ne': ''}},
            {'completion_date': {'$exists': True}}
        ]}
    ).count()

    send('Import finished: '
         '{} new assessments, '
         'total now {}, '
         '{} completed'.format(
         imported - existing,
         imported,
         completed
    ))


def get_kits_by_pcode(p_code, status=""):

    query = [
        {'$match': {'type': 'assessment', 'location.p_code': p_code}},
        {'$project': {'kits': '$child_list.kit'}},
        {'$unwind': '$kits'},
        {'$group': {'_id': "$kits", 'count': {'$sum': 1}}},
    ]
    if status:
        query.insert(
            0,
            {'$match': {'child_list': {'$elemMatch': {'status': status}}}}
        )

    kits = winter.data.aggregate(query)
    return kits['result']


def prepare_manifest():

    sites = winter.data.aggregate([
        {'$project': {'site': '$location.p_code'}},
        {'$group': {'_id': '$site'}}
    ])['result']
    for location in sites:
        p_code = location['_id']
        if not p_code:
            continue
        assessments = list(winter.data.find(
            {'$and': [
                {'type': 'assessment'},
                {'location.p_code': p_code},
                {'completed': {'$exists': True}}
        ]}))
        if not assessments:
            continue
        completed_num = winter.data.find(
            {'$and': [
                {'type': 'assessment'},
                {'location.p_code': p_code},
                {'completed': True},
                {'completed': {'$exists': True}}
        ]}).count()
        kits = get_kits_by_pcode(p_code)
        if kits:
            site = winter.sites.find_one(
                {'p_code': p_code},
                {
                    'pcodename': 1,
                    'mohafaza': 1,
                    'district': 1,
                    'cadastral': 1,
                    'municipaliy': 1,
                    'no_tent': 1,
                    'no_ind': 1,
                    'lat': 1,
                    'long': 1,
                    'elevation': 1,
                    'confirmed_ip': 1,
                    'unicef_priority': 1
                }
            )
            start_date = sorted(assessments, key=itemgetter('creation_date'), reverse=True)[0]['creation_date']
            start_date = unidecode.unidecode(start_date)
            start_date = dateutil.parser.parse(start_date).strftime('%Y-%m-%d') if start_date else ''
            end_date = sorted(assessments, key=itemgetter('completion_date'), reverse=True)[0]['completion_date']
            end_date = dateutil.parser.parse(end_date).strftime('%Y-%m-%d') if end_date else ''
            site['actual_ip'] = assessments[-1]['history'][-1]['organisation']
            site['assessment_date'] = start_date
            site['num_assessments'] = len(assessments)
            site['completed'] = completed_num
            site['remaining'] = len(assessments) - completed_num
            site['distribution_date'] = end_date

            total = 0
            for kit in kits:
                site[kit['_id']] = kit['count']
                total += kit['count']
            site['total_kits'] = total

            total_completed = 0
            for completed in get_kits_by_pcode(p_code, status='COMPLETED'):
                site['Completed ' + completed['_id']] = completed['count']
                total_completed += completed['count']
            site['total_completed'] = total_completed

            total_remaining = 0
            for remaining in get_kits_by_pcode(p_code, status='ALLOCATED'):
                site['Remaining ' + remaining['_id']] = remaining['count']
                total_remaining += remaining['count']
            site['total_remaining'] = total_remaining

            status = 'assessed'
            if completed_num == len(assessments):
                status = 'completed'
            elif completed_num:
                status = 'distributing'
            site['status'] = status

            client.sql(
                "UPDATE {} SET winterization_status = \'{}\' WHERE p_code_winter = \'{}\'".format(
                    'imap8_winter',
                    status,
                    p_code
                )
            )

            winter.manifest.update({'_id': p_code}, site, upsert=True)

    send('Manifest prepared for {} sites'.format(
        winter.manifest.find().count()
    ))
