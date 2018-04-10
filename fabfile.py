from fabric.api import local


def update_requirements():
    local('pip-compile EquiTrack/requirements/input/base.in '
          '--no-header '
          '--no-emit-trusted-host '
          '--no-index -o EquiTrack/requirements/base.txt')
    local('pip-compile EquiTrack/requirements/base.txt EquiTrack/requirements/input/production.in '
          '--no-header '
          '--no-emit-trusted-host '
          '--no-index -o EquiTrack/requirements/production.txt')
    local('pip-compile EquiTrack/requirements/base.txt EquiTrack/requirements/input/test.in '
          '--no-header '
          '--no-emit-trusted-host '
          '--no-index -o EquiTrack/requirements/test.txt')
    local('pip-compile EquiTrack/requirements/test.txt '
          'EquiTrack/requirements/input/local.in '
          '--no-header '
          '--no-emit-trusted-host '
          '--no-index -o EquiTrack/requirements/local.txt')


def install_requirements(env_name='production'):
    local('pip-sync EquiTrack/requirements/{}.txt'.format(env_name))
