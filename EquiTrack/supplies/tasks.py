__author__ = 'jcranwellward'

import datetime
import json
import os

import requests
from django.conf import settings
from django.db import connection
from requests.auth import HTTPBasicAuth

from EquiTrack.celery import app
from celery.utils.log import get_task_logger


logger = get_task_logger(__name__)


def set_docs(docs):

    payload_json = json.dumps(
        {
            'docs': docs,
            'all_or_nothing': True
        }
    )
    path = os.path.join(settings.COUCHBASE_URL, '_bulk_docs')
    response = requests.post(
        path,
        headers={'content-type': 'application/json'},
        auth=HTTPBasicAuth(settings.COUCHBASE_USER, settings.COUCHBASE_PASS),
        data=payload_json,
    )
    return response


@app.task
def set_unisupply_user(username, password):

    user_docs = []
    user_docs.append(
        {
            "_id": username,
            "type": "user",
            "country": connection.schema_name,
            "username": username,
            "password": password,
            "organisation": username,
        }
    )

    response = set_docs(user_docs)
    return response.text


@app.task
def set_unisupply_distribution(distribution_plan_id):
    """
    Creates or edits a distibution document in Couchbase
    """
    from partners.models import DistributionPlan
    distribution_plan = DistributionPlan.objects.get(id=distribution_plan_id)

    logger.debug('Unisupply: set_unisupply_distribution task initiated')

    doc = distribution_plan.document if distribution_plan.document else {
        "country": connection.schema_name,
        "distribution_id": distribution_plan.id,
        "intervention": distribution_plan.partnership.__unicode__(),
        "partner_name": distribution_plan.partnership.partner.short_name,
        "icon": "institution",
        "criticality": "0",
        "item_list": [
            {
                "item_type": distribution_plan.item.name,
                "quantity": distribution_plan.quantity,
                "delivered": 0
            }
        ],
        "location": {
            "location_type": distribution_plan.site.gateway.name,
            "p_code": distribution_plan.site.p_code,
            "p_code_name": distribution_plan.site.name,
        },
        "type": "distribution",
        "name": distribution_plan.site.name,
        "completed": False,
        "creation_date": datetime.datetime.now().isoformat()
    }

    doc["item_list"][0]["quantity"] = distribution_plan.quantity
    doc["item_list"][0]["delivered"] = distribution_plan.delivered

    response = set_docs([doc])
    if response.status_code in [requests.codes.ok, requests.codes.created]:
        # TODO: Check if it was actually saved by couchbase
        distribution_plan.send = False
        distribution_plan.sent = True
        distribution_plan.save()

    logger.info('Unisupply task completed'
                'Status:{}, Sent:{}, Id:{}'.format(response.status_code,
                                                   distribution_plan.sent,
                                                   distribution_plan.id))
    return response.text


@app.task
def import_docs(**kwargs):
    """
    Imports docs from couch base
    """
    from partners.models import DistributionPlan

    data = requests.get(
        os.path.join(settings.COUCHBASE_URL, '_all_docs?include_docs=true'),
        auth=HTTPBasicAuth(settings.COUCHBASE_USER, settings.COUCHBASE_PASS)
    ).json()

    for row in data['rows']:
        if 'distribution_id' in row['doc']:
            distribution_id = row['doc']['distribution_id']
            try:
                connection.set_schema(row['doc']['country'])
                distribution = DistributionPlan.objects.get(
                    id=distribution_id
                )
                distribution.delivered = row['doc']['item_list'][0]['delivered']
                distribution.document = row['doc']
                distribution.save()
            except DistributionPlan.DoesNotExist:
                print 'Distribution ID {} not found for Country {}'.format(
                    distribution_id, row['doc']['country']
                )
            except Exception as exp:
                print exp.message
