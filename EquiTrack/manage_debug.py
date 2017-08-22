#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":

    try:
        sys.path.append("/code/pycharm-debug.egg")
    except:
        sys.stderr.write("Error: " +
                         "You must add pycharm-debug.egg to your main EquiTrack folder ")
        sys.exit(1)
    from django.core.management import execute_from_command_line
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "EquiTrack.settings.local")
    DEBUG_IP = os.environ.get("DEBUG_IP", "10.0.2.2")
    DEBUG_PORT = int(os.environ.get("DEBUG_PORT", 51312))
    if len(sys.argv) > 1:
        command = sys.argv[1]

    if (command == "runserver" or command == "testserver"):

        # Make pydev debugger works for auto reload.
        try:
            import pydevd
        except ImportError:
            sys.stderr.write(
                "Error: " +
                "Could not import pydevd. make sure your pycharm-debug.egg is in the main EquiTrack folder")
            sys.exit(1)

        from django.utils import autoreload
        m = autoreload.main

        def main(main_func, args=None, kwargs=None):
            if os.environ.get("RUN_MAIN") == "true":
                def pydevdDecorator(func):
                    def wrap(*args, **kws):
                        pydevd.settrace(DEBUG_IP, port=DEBUG_PORT, suspend=False, stdoutToServer=True,
                                        stderrToServer=True)
                        return func(*args, **kws)
                    return wrap
                main_func = pydevdDecorator(main_func)

            return m(main_func, args, kwargs)

        autoreload.main = main

    execute_from_command_line(sys.argv)
