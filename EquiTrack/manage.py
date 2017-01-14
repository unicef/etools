#!/usr/bin/env python
import os
# import sys
#
#
# if __name__ == "__main__":
#     sys.path.append("/code/pycharm-debug.egg")
#     import pydevd
#
#     try:
#         pydevd.settrace('192.168.86.193', port=51312, suspend=False, stdoutToServer=True, stderrToServer=True)
#     except:
#         print 'boo'
#
#     print 'boo anyway'
#     os.environ.setdefault("DJANGO_SETTINGS_MODULE", "EquiTrack.settings.local")
#     from django.core.management import execute_from_command_line
#
#     execute_from_command_line(sys.argv)
#
# #!/usr/bin/env python
# from django.core.management import execute_manager
# try:
#    import settings # Assumed to be in the same directory.
# except ImportError:
#    import sys
#    sys.stderr.write("Error: Can't find the file 'settings.py' in the  directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
#    sys.exit(1)


if __name__ == "__main__":


    import sys

    sys.path.append("/code/pycharm-debug.egg")
    from django.core.management import execute_from_command_line
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "EquiTrack.settings.local")
    if len(sys.argv) > 1:
        command = sys.argv[1]

    if (command == "runserver" or command == "testserver"):

        # Make pydev debugger works for auto reload.
        try:
           import pydevd
        except ImportError:
           sys.stderr.write("Error: " +
               "You must add org.python.pydev.debug.pysrc to your PYTHONPATH.")
           sys.exit(1)

        from django.utils import autoreload
        m = autoreload.main
        def main(main_func, args=None, kwargs=None):
           import os
           if os.environ.get("RUN_MAIN") == "true":
               def pydevdDecorator(func):
                   def wrap(*args, **kws):
                       pydevd.settrace('192.168.86.193', port=51312, suspend=False, stdoutToServer=True,
                                       stderrToServer=True)
                       return func(*args, **kws)
                   return wrap
               main_func = pydevdDecorator(main_func)

           return m(main_func, args, kwargs)

        autoreload.main = main

    execute_from_command_line(sys.argv)