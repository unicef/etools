__author__ = 'jcranwellward'

from fabric.api import local, sudo, get, run, shell_env


def dump_db(name='EquiTrack'):

    run('pg_dump -Fc --no-acl --no-owner -h localhost -U {dbuser} {dbname} > /tmp/latest.dump'.format(
        dbname=name,
        dbuser=name,
    ))
    get('/tmp/local.dump')


def load_db_dump(name='equitrack'):

    local('pg_restore --verbose --clean --no-acl --no-owner -h localhost -d {} latest.dump'.format(name))


def dump_load_db(capture=False):

    get_db_dump(capture)
    load_db_dump()