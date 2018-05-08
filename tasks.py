# -*- coding: utf-8 -*-
from invoke import task


@task
def update_requirements(ctx):
    """Update requirements for all environments"""
    ctx.run(
        'pip-compile src/requirements/input/base.in '
        '--no-header '
        '--no-emit-trusted-host '
        '--no-index -o src/requirements/base.txt'
    )
    ctx.run(
        'pip-compile src/requirements/base.txt src/requirements/input/production.in '
        '--no-header '
        '--no-emit-trusted-host '
        '--no-index -o src/requirements/production.txt'
    )
    ctx.run(
        'pip-compile src/requirements/base.txt src/requirements/input/test.in '
        '--no-header '
        '--no-emit-trusted-host '
        '--no-index -o src/requirements/test.txt'
    )
    ctx.run(
        'pip-compile src/requirements/test.txt '
        'src/requirements/input/local.in '
        '--no-header '
        '--no-emit-trusted-host '
        '--no-index -o src/requirements/local.txt'
    )


@task(help={"env": "Environment to install"})
def install_requirements(ctx, env='production'):
    """Install requirements for specified environment"""
    ctx.run('pip-sync src/requirements/{}.txt'.format(env))
