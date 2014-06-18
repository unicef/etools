__author__ = 'jcranwellward'

from fabric.api import local, sudo, get, run, shell_env, env

env.roledefs = {
    'dev': ['localhost'],
    'staging': ['staging.equitrack.uniceflebanon.org'],
    'production': ['equitrack.uniceflebanon.org']
}


def dump_db(name='EquiTrack'):

    run('pg_dump -Fc --no-acl --no-owner -h localhost -U {dbuser} {dbname} > /tmp/latest.dump'.format(
        dbname=name,
        dbuser=name,
    ))
    get('/tmp/latest.dump', local_path='deployment/{}-latest.dump'.format(name))


def load_db_dump(name='equitrack'):

    local('pg_restore --verbose --clean --no-acl --no-owner -d {} latest.dump'.format(name))


