Development Environment Setup Instructions (OSX)
================================================

Setup Server
------------
Step 1. Install latest python

```bash
$ brew install python
```

Step 2. Install Postgres with brew, create Postgres database, and run the Postgres upon startup

```bash
$ brew install postgresql
$ initdb /usr/local/var/postgres
$ mkdir -p ~/Library/LaunchAgents
$ ln -sfv /usr/local/opt/postgresql/*.plist ~/Library/LaunchAgents
$ launchctl load ~/Library/LaunchAgents/homebrew.mxcl.postgresql.plist
```

Step 3. Install PostGIS and connect to database:

```bash
$ brew install postgis
$ psql postgres
```

Step 4. Create Postgres user and PostGIS required extensions:

```bash
# CREATE ROLE postgres WITH superuser login;
# CREATE EXTENSION postgis;
# CREATE EXTENSION postgis_topology;
# CREATE EXTENSION fuzzystrmatch;
# \q
```

Step 5. Install Redis:

```bash
$ brew install redis
```

Step 6. Clone EquiTrack repository

```bash
$ git clone https://github.com/UNICEFLebanonInnovation/EquiTrack.git .
$ git checkout etools
```

Step 6. Install VirtualEnv and VirtualEnvWrapper, create Virtual Environment and load Python packages

```bash
$ pip install virtualenv
$ pip install virtualenvwrapper
$ export WORKON_HOME=~/Envs
$ export VIRTUALENVWRAPPER_PYTHON=/usr/local/bin/python2.7
$ mkdir -p $WORKON_HOME
$ source /usr/local/bin/virtualenvwrapper.sh
$ mkvirtualenv env1
$ pip install -r EquiTrack/requirements/base.txt
```

Step 7. Set environment variables:

```bash
$ export REDIS_URL=redis://localhost:6379/0
$ export DATABASE_URL=postgis://postgres:password@localhost:5432/postgres
```

Step 8. Migrate database schemas and create database superuser

```bash
$ python manage.py migrate_schemas --fake-initial --noinput
$ python manage.py createsuperuser
```

Run Server
----------

```bash
$ source ~/.virtualenvs/env1/bin/activate
$ export DATABASE_URL=postgis://postgres:password@localhost:5432/postgres
$ python EquiTrack/manage.py runserver 8080
```

Load Default Data
-----------------

Step 1. Login to the Admin Portal using the super user account:

```bash
http://127.0.0.1:8080/admin/login/
```

Step 2. In the Admin Portal, add a country (required for availability of other database tables)

```bash
http://127.0.0.1:8080/admin/users/country/add/
```

Step 3. Create a user profile with the previously created country:

```bash
http://127.0.0.1:8080/admin/users/userprofile/add/
```

Setup Debugger (PyCharm)
------------------------

Step 1:
* Once the project is loaded in PyCharm go to menu -&gt; <code>PyCharm - &gt; Preferences -&gt; Project</code>
* Make sure your project is chosen
* Select the python interpreter present inside of the virtualenvironment

Step 2:
* Go to menu -&gt; <code>PyCharm - &gt; Preferences -&gt; Languages &amp; Frameworks -&gt; Django</code>
* Select your project and:
    * enable Django Support
    * Set Django Project root
    * choose base.py as the settings file
    * add all of the previously mentioned environment vars

Step 3:
* Go to menu -&gt; <code>Run -&gt; Edit Configurations</code>
* Add Django Server and name it.
* In the Configuration make sure to add the environment variables again
* Choose the python interpreter (The interpreter inside of the virtual environment)
* Choose a working Directory

Step 4:
* Quit Pycharm and restart it

Resources
---------
http://www.gotealeaf.com/blog/how-to-install-postgresql-on-a-mac

http://jasdeep.ca/2012/05/installing-redis-on-mac-os-x/

https://virtualenv.pypa.io/en/latest/userguide.html

https://www.jetbrains.com/pycharm/help/run-debug-configuration.html

http://postgis.net/install

http://virtualenvwrapper.readthedocs.org/en/latest/index.html