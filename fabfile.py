__author__ = 'jcranwellward'

from fabric.api import local


def get_db_dump(capture=False):

    if capture:
        local('heroku pgbackups:capture')
    local('curl -o latest.dump `heroku pgbackups:url`')


def dump_local_db(name='equitrack'):

    local('pg_dump -Fc --no-acl --no-owner -h localhost {} > latest.dump'.format(name))


def load_db_dump(name='equitrack'):

    local('pg_restore --verbose --clean --no-acl --no-owner -h localhost -d {} latest.dump'.format(name))


def dump_load_db():

    get_db_dump()
    load_db_dump()