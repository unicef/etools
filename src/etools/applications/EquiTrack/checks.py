# -*- coding: utf-8 -*-
# import io
#
# from django.core.checks import Error, register
# from django.core.management import call_command
#
#
# @register()
# def example_check(app_configs, **kwargs):
#     errors = []
#     out = io.StringIO()
#     try:
#         call_command('makemigrations', check_changes=True, verbosity=0,
#                      dry_run=True, stdout=out)
#     except SystemExit:
#         errors.append(
#             Error(
#                 out.read(),
#                 hint='run ./manage.py makemigrations',
#                 obj=None,
#                 id='etools.E001',
#             )
#         )
#     return errors
