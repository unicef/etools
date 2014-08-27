from __future__ import with_statement

"""Fabric server config management fabfile.
If you need additional configuration, setup ~/.fabricrc file:

    user = your_remote_server_username

To get specific command help type:
    fab -d command_name

"""

import os

from fabric.utils import puts
from fabric import colors
import fabric.network
import fabric.state
from StringIO import StringIO
from fabric.api import (
    local,
    settings,
    abort,
    run,
    cd,
    env,
    get,
    warn_only,
    sudo
)
from fabric.contrib.files import exists


YAML_AVAILABLE = True
try:
    import yaml
except ImportError:
    YAML_AVAILABLE = False


JSON_AVAILABLE = True
try:
    import simplejson as json
except ImportError:
    try:
        import json
    except ImportError:
        JSON_AVAILABLE = False

################################
#         ENVIRONMENTS         #
################################


def _load_config(**kwargs):
    """Find and parse server config file.

    If `config` keyword argument wasn't set look for default
    'server_config.yaml' or 'server_config.json' file.

    """
    config, ext = os.path.splitext('server_config.yaml' if os.path.exists('server_config.yaml') else 'server_config.json')

    if not os.path.exists(config + ext):
        print colors.red('Error. "%s" file not found.' % (config + ext))
        return {}
    if YAML_AVAILABLE and ext == '.yaml':
        loader = yaml
    elif JSON_AVAILABLE and ext =='.json':
        loader = json
    else:
        print colors.red('Parser package not available')
        return {}
    # Open file and deserialize settings.
    with open(config + ext) as config_file:
        return loader.load(config_file)


def s(*args, **kwargs):
    """Set destination servers or server groups by comma delimited list of names"""
    # Load config
    servers = _load_config(**kwargs)
    # If no arguments were recieved, print a message with a list of available configs.
    if not args:
        print 'No server name given. Available configs:'
        for key in servers:
            print colors.green('\t%s' % key)

    # Create `group` - a dictionary, containing copies of configs for selected servers. Server hosts
    # are used as dictionary keys, which allows us to connect current command destination host with
    # the correct config. This is important, because somewhere along the way fabric messes up the
    # hosts order, so simple list index incrementation won't suffice.
    env.group = {}
    # For each given server name
    for name in args:
        #  Recursive function call to retrieve all server records. If `name` is a group(e.g. `all`)
        # - get it's members, iterate through them and create `group`
        # record. Else, get fields from `name` server record.
        # If requested server is not in the settings dictionary output error message and list all
        # available servers.
        _build_group(name, servers)


    # Copy server hosts from `env.group` keys - this gives us a complete list of unique hosts to
    # operate on. No host is added twice, so we can safely add overlaping groups. Each added host is
    # guaranteed to have a config record in `env.group`.
    env.hosts = env.group.keys()


def _build_group(name, servers):
    """Recursively walk through servers dictionary and search for all server records."""
    # We're going to reference server a lot, so we'd better store it.
    server = servers.get(name, None)
    # If `name` exists in servers dictionary we
    if server:
        # check whether it's a group by looking for `members`
        if isinstance(server, list):
            if fabric.state.output['debug']:
                    puts("%s is a group, getting members" % name)
            for item in server:
                # and call this function for each of them.
                _build_group(item, servers)
        # When, finally, we dig through to the standalone server records, we retrieve
        # configs and store them in `env.group`
        else:
            if fabric.state.output['debug']:
                    puts("%s is a server, filling up env.group" % name)
            env.group[server['host']] = server
    else:
        print colors.red('Error. "%s" config not found. Run `fab s` to list all available configs' % name)


def _setup(task):
    """
    Copies server config settings from `env.group` dictionary to env variable.

    This way, tasks have easier access to server-specific variables:
        `env.owner` instead of `env.group[env.host]['owner']`

    """
    def task_with_setup(*args, **kwargs):
        # If `s:server` was run before the current command - then we should copy values to
        # `env`. Otherwise, hosts were passed through command line with `fab -H host1,host2
        # command` and we skip.
        if env.get("group", None):
            for key, val in env.group[env.host].items():
                setattr(env, key, val)
                if fabric.state.output['debug']:
                    puts("[env] %s : %s" % (key, val))

        task(*args, **kwargs)
        # Don't keep host connections open, disconnect from each host after each task.
        # Function will be available in fabric 1.0 release.
        # fabric.network.disconnect_all()
    return task_with_setup


#############################
#          TASKS            #
#############################


def get_id_of_running_image(image):
    print('>>> Get current container id if exists')
    CID = run("docker ps | grep {} | awk '{{print $1}}'".format(image))
    return CID


def snapshot_container_to_image(container, image, tag):
    print('>>> Committing current container')
    run('docker commit {} {}:{}'.format(container, image, tag))

@_setup
def dump_image_to_archive():
    run('docker save {} > {}.tar'.format(env.image, env.name))
    run('gzip {}.tar'.format(env.name))
    get('{}.tar.gz'.format(env.name))


def load_image_from_archive(name):
    with warn_only():
        run('gunzip {}.tar.gz'.format(name))
    run('docker load < {}.tar'.format(name))


def get_latest_image(image, name):
    current = get_id_of_running_image(image)
    snapshot_container_to_image(current, image, 'latest')
    dump_image_to_archive(env.image, name)


def build_image_with_packer(from_image, to_image='', tag='latest', packer_file='packer.json'):
    print('>>> Building new image with file {}'.format(packer_file))
    if not to_image:
        to_image = from_image
    run("/usr/local/packer/packer build -var 'from_image={from_image}' -var 'to_image={to_image}' -var 'tag={tag}' {file}".format(
        file=packer_file,
        from_image=from_image,
        to_image=to_image,
        tag=tag
    ))


def docker_ps(all=False):
    run('docker ps {}'.format('-a' if all else ''))


def docker_images():
    return run('docker images')


def remove_image(image):
    run('docker rmi {}'.format(image))


def remove_container(container):
    stop_container(container)
    print('>>> Removing container {}'.format(container))
    run('docker rm -f {}'.format(container))


def stop_container(container):
    print('>>> Stopping container {}'.format(container))
    run('docker stop {}'.format(container))


def clean_containers():
    print('>>> Cleaning up containers')
    run("docker ps -a | grep 'Exit' | awk '{print $1}' | while read -r id ; do\n docker rm $id \ndone")


def clean_images():
    print('>>> Cleaning up images')
    run('docker images | grep "^<none>" | awk \'BEGIN { FS = "[ \t]+" } { print $3 }\'  | while read -r id ; '
        'do\n docker rmi $id\n done')


@_setup
def start_container():
    print('>>> Starting new container for image {}'.format(env.image))
    run(
        'docker run --name={name} -p={port} {envs} -d {image} {command}'.format(
        name=env.name, image=env.image, port=env.ports, command=env.run, envs=' '.join(
            ['-e "{}={}"'.format(key, value) for key, value in env.envs.items()])
        )
    )


@_setup
def deploy():
    # pull new code from github
    with cd(env.git_dir):
        run("git pull origin {}".format(env.branch))
        current = get_id_of_running_image(env.image)
        print current
        if not current:
            build_image_with_packer(env.image, env.image)
        else:
            snapshot_container_to_image(current, env.image, 'latest')
            build_image_with_packer(env.image, env.image)
            stop_container(current)
            snapshot_container_to_image(current, env.image, 'backup')
            remove_container(current)

        start_container()


@_setup
def get_env_vars():
    run('dokku config {}'.format(env.name))


@_setup
def set_env_vars():
    run('dokku config:set {app} {envs}'.format(
        app=env.name,
        envs=' '.join(
            ['{}={}'.format(key, value)
             for key, value in env.envs.items()])
    ))


@_setup
def create_db(restore=False):
    cmd = 'dokku postgis:{} ' + env.name
    if restore:
        with settings(warn_only=True):
            run(cmd.format('delete'))
    run(cmd.format('create'))
    if restore:
        run(cmd.format('restore')+' < /home/dokku/{}/backup.sql'.format(env.name))


@_setup
def link_db():
    run('dokku postgis:link {} {}'.format(env.name, env.name))


@_setup
def migrate_db(backup=True):
    if backup:
        run('dokku postgis:dump {} > /home/dokku/{}/backup.sql'.format(env.name, env.name))
    run('dokku run {} python EquiTrack/manage.py syncdb --migrate'.format(env.name))


@_setup
def create():
    with settings(warn_only=True):
        local('git remote add {app} dokku@{host}:{app}'.format(
            app=env.name, host=env.host
        ))
    deploy_app()
    create_db()
    migrate_db()


@_setup
def rebuild():
    run('dokku rebuild {}'.format(env.name))


@_setup
def shell():
    run('dokku run {} python EquiTrack/manage.py shell'.format(env.name))


@_setup
def deploy_app(migrate=False):
    local('git push {app} {branch}:master'.format(
        app=env.name, branch=env.branch
    ))
    if migrate:
        migrate_db()
    clean_containers()
    clean_images()


