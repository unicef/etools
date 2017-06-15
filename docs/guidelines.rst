Developer Guidelines
====================

This document lists guidelines that we expect developers to follow when contributing to eTools. It
is always a work-in-progress.


Code Style
----------

We follow `PEP-8 <https://www.python.org/dev/peps/pep-0008/>`_, as amended on 01-Aug-2013. Please
read it. It has a lot of useful advice that won't be repeated here. We use `flake8
<https://pypi.python.org/pypi/flake8>`_ to enforce this. Flake8 is run during continuous integration
and developers should run it locally prior to submitting a PR for review.


Flake8 exceptions
~~~~~~~~~~~~~~~~~

We allow the following flake8 "rules" to be violated:

* E121 and E126: These rules specify the proper amount of "hanging indent" for multi-line
  statements. We allow them to be violated.
* max-line-length: The default maximum is 80 characters, which we have increased to 120 characters.


Organizing imports
~~~~~~~~~~~~~~~~~~

We organize imports into the following groups, in the following order. (This is an extension of
`PEP-8's guidance <https://www.python.org/dev/peps/pep-0008/#imports>`_).

* Imports from `__future__`
* Imports from the Python standard library
* Anything not in the other categories goes here - possibly subdivided.
* Imports from code in the same project/repository.

Within a group, lines are alphabetized, ignoring the first word ("from" or "import").
E.g.::

    from datetime import timedelta
    import os
    from os.path import abspath
    from sys import exit

Per PEP-8, "You should put a blank line between each group of imports.".


Python 3 Prep
~~~~~~~~~~~~~

To make your code easier to port to Python 3, add the following to the top of
all new files::

	from __future__ import division
	from __future__ import absolute_import
	from __future__ import print_function
	from __future__ import unicode_literals

You can also add them to existing files, but be aware that they may change
the behavior of your code (particularly the default use of unicode literals).
