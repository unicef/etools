__author__ = 'jcranwellward'

from activtyinfo_client import ActivityInfoClient

from .models import (
    Database,
    Activity,
    Indicator,
    Partner,
)


def import_database(db_id, username, password):
    """
    Import all activities, indicators and partners from
    a ActivityInfo database specified by the passed ID
    """
    if Database.objects.exists(ai_id=db_id):
        raise Exception('The database already exists,'
                        'please delete before importing.')

    client = ActivityInfoClient(username, password)

    databases = client.get_databases()
    db_ids = [db['id'] for db in databases]
    if db_id not in db_ids:
        raise Exception('Database not found in ActivityInfo')

    db_info = client.get_database(db_id)
    database = Database()
    database.ai_id = db_id
    database.name = db_info['name']
    database.description = db_info['description']
    database.ai_country_id = db_info['country']['id']
    database.country_name = db_info['country']['name']
    database.save()

    for partner in db_info['partners']:
        Partner.objects.get_or_create(
            ai_id=partner['id'],
            name=partner['name'],
            full_name=partner['fullName'],
            database=database
        )

    for activity in db_info['activities']:
        ai_activity, created = Activity.objects.get_or_create(
            ai_id=activity['id'],
            name=activity['name'],
            location_type=activity['locationType']['name'],
            database=database
        )
        for indicator in activity['indicators']:
            ai_indicator, created = Indicator.objects.get_or_create(
                ai_id=indicator['id'],
                name=indicator['name'],
                description=indicator['description'],
                units=indicator['units'],
                category=indicator['category'],
                activity=activity
            )

