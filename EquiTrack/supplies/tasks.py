__author__ = 'jcranwellward'

import os
import json
import requests
import datetime

from django.db import connection
from django.conf import settings
from django.template.defaultfilters import slugify

from requests.auth import HTTPBasicAuth
from tenant_schemas.utils import tenant_context

from EquiTrack.celery import app
from users.models import Country


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
            "channels": ["users"],
            "username": username,
            "password": password,
            "organisation": username,
        }
    )

    response = set_docs(user_docs)
    return response.text


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
                "country": connection.schema_name,
                "distribution_id": distribution_plan.id,
                "intervention": "{}: {}".format(
                    distribution_plan.partnership.number,
                    distribution_plan.partnership.title),
                "channels": [distribution_plan.partnership.partner.short_name.lower()],
                "partner_name": distribution_plan.partnership.partner.short_name,
                "icon": "institution",
                "criticality": "0",
                "item_list": [
                    {
                        "item_type": distribution_plan.item.name,
                        "quantity": distribution_plan.quantity
                    }
                ],
                "location": {
                    "location_type": distribution_plan.location.gateway.name,
                    "p_code": distribution_plan.location.p_code,
                    "p_code_name": distribution_plan.location.name,
                },
                "type": "distribution",
                "completed": False,
                "creation_date": datetime.datetime.now().isoformat(),
                "name": distribution_plan.location.name,
            }
        ])
        if response.status_code in [requests.codes.ok, requests.codes.created]:

            distribution_plan.send = False
            distribution_plan.sent = True
            distribution_plan.save()

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

    countries = Country.objects.all().exclude(schema_name='public')

    for country in countries:
        with tenant_context(country):

            for row in data['rows']:
                if 'distribution_id' in row['doc']:
                    distribution_id = row['doc']['distribution_id']
                    try:
                        distribution = DistributionPlan.objects.get(
                            id=distribution_id
                        )
                    except DistributionPlan.DoesNotExist:
                        print 'Distribution ID {} not found for Country {}'.format(
                            distribution_id, country.name
                        )
                    else:
                        distribution.delivered = row['doc']['item_list'][0]['delivered']
                        distribution.save()

