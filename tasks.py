# -*- coding: utf-8 -*-
import os

from invoke import task

BASE_DIR = "{}/".format(os.path.dirname(os.path.abspath(__file__)))


@task
def update_requirements(ctx):
    """Update requirements for all environments"""
    ctx.run(
        'pip-compile {0}src/requirements/input/base.in '
        '--no-header '
        '--no-emit-trusted-host '
        '--no-index -o {0}src/requirements/base.txt'.format(BASE_DIR)
    )
    ctx.run(
        'pip-compile {0}src/requirements/base.txt '
        '{0}src/requirements/input/production.in '
        '--no-header '
        '--no-emit-trusted-host '
        '--no-index -o {0}src/requirements/production.txt'.format(
            BASE_DIR
        )
    )
    ctx.run(
        'pip-compile {0}src/requirements/base.txt '
        '{0}src/requirements/input/test.in '
        '--no-header '
        '--no-emit-trusted-host '
        '--no-index -o {0}src/requirements/test.txt'.format(BASE_DIR)
    )
    ctx.run(
        'pip-compile {0}src/requirements/test.txt '
        '{0}src/requirements/input/local.in '
        '--no-header '
        '--no-emit-trusted-host '
        '--no-index -o {0}src/requirements/local.txt'.format(BASE_DIR)
    )


@task(help={"env": "Environment to install"})
def install_requirements(ctx, env='production'):
    """Install requirements for specified environment"""
    ctx.run('pip-sync {0}src/requirements/{1}.txt'.format(BASE_DIR, env))
