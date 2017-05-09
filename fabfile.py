from fabric.api import local, settings
from fabric.contrib import django


def fetch_source():
    local('git fetch origin')
    local('git reset --hard origin/puli_test_server_branch')

def migrate_schemas():
    local('python EquiTrack/manage.py migrate_schemas')

def run_server():
    local('screen -X quit')
    local('screen -d -m python EquiTrack/manage.py runserver 0.0.0.0:9090')

def update():
    fetch_source()
    migrate_schemas()
    run_server()

def import_dump(url):
    local('dropdb postgres && createdb postgres')

    local('curl -O {}'.format(url))
    filename = url.split('/').pop()
    ext = filename.split('.')[-1]
    # pg_restore will probably throw some errors that needs to be ignored
    with settings(warn_only=True):
        if ext == 'bz2':
            local('bzcat {} | sudo -u postgres nice pg_restore --verbose -F t -d postgres'.format(filename))
        if ext == 'sql':
            local('cat {} | nice pg_restore --verbose -d postgres -U postgres'.format(filename))

    local('cat create_test_user.py | python EquiTrack/manage.py shell_plus')

    migrate_schemas()
