# -*- coding: utf-8 -*-
from invoke import task


@task
def update_requirements(ctx):
    ctx.run(
        'pip-compile EquiTrack/requirements/input/base.in '
        '--no-header '
        '--no-emit-trusted-host '
        '--no-index -o EquiTrack/requirements/base.txt'
    )
    ctx.run(
        'pip-compile EquiTrack/requirements/base.txt EquiTrack/requirements/input/production.in '
        '--no-header '
        '--no-emit-trusted-host '
        '--no-index -o EquiTrack/requirements/production.txt'
    )
    ctx.run(
        'pip-compile EquiTrack/requirements/base.txt EquiTrack/requirements/input/test.in '
        '--no-header '
        '--no-emit-trusted-host '
        '--no-index -o EquiTrack/requirements/test.txt'
    )
    ctx.run(
        'pip-compile EquiTrack/requirements/test.txt '
        'EquiTrack/requirements/input/local.in '
        '--no-header '
        '--no-emit-trusted-host '
        '--no-index -o EquiTrack/requirements/local.txt'
    )


@task
def install_requirements(ctx, env='production'):
    ctx.run('pip-sync EquiTrack/requirements/{}.txt'.format(env))
