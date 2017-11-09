Development Environment Setup Instructions (Ubuntu)
===================================================

The UNICEF eTools repo represents the backend of the eTools application. In order to see the full
application in action, ignore this document and instead follow the steps in the [etools-infra
README](https://github.com/unicef/etools-infra#etools-backend-infrastructure-configuration).

Some developers, however, may wish to focus only on the backend. If so, these instructions will help
you get the backend running on your laptop without needing Docker or any of the other frontend
applications. This will allow you to run tests, use the Django shell, and view the Django admin.

Requirements
------------

These instructions assume you are starting with Ubuntu 16.04.

Set up Python and Postgres
--------------------------

This step is unnecessary if you already have Python 2.7, Postgres 9.5, and PostGIS 2.2 installed on
your machine.

```bash
$ sudo apt update
$ sudo apt install python2.7 python-pip virtualenv libgdal-dev \
                   postgresql postgresql-9.5-postgis-2.2 libpq-dev
```

Prepare Postgres
----------------

This step is unnecessary if your user can create databases, and if you already
have installed some commonly used extensions into your template1 database.

```bash
$ sudo -u postgres createuser <your-username> --createdb
$ sudo -u postgres psql template1 -c "create extension hstore;"
$ sudo -u postgres psql template1 -c "create extension postgis;"
$ sudo -u postgres psql template1 -c "create extension pg_trgm;"
```

Set up virtualenvwrapper
------------------------

This step is unnecessary if you have already installed virtualenvwrapper previously.

Add the following statements to your `.profile`. See the [virtualenvwrapper
documentation](https://virtualenvwrapper.readthedocs.io/en/latest/install.html#shell-startup-file)
for details on the values you should use.

```bash
$ pip install virtualenvwrapper
$ source virtualenvwrapper.sh
```

Get the code
------------

```bash
$ git clone git@github.com:unicef/etools.git
$ cd etools/EquiTrack/
```

Install the pip requirements
----------------------------

Installing GDAL requires us to point to the proper location of the GDAL header files.

```bash
$ export CPLUS_INCLUDE_PATH=/usr/include/gdal
$ export C_INCLUDE_PATH=/usr/include/gdal
$ mkvirtualenv -p `which python2.7` etools
(etools)$ pip install -r requirements/local.txt
```

Set up your database
--------------------

```bash
(etools)$ createdb etools
(etools)$ python manage.py migrate_schemas --noinput
(etools)$ python manage.py createsuperuser
```

Run the server
--------------

```bash
(etools)$ python manage.py runserver
```

Run lint and tests
------------------

```bash
(etools)$ ./runtests.sh
```

Run tests on just one module
----------------------------

```bash
(etools)$ ./runtests.sh partners
```
