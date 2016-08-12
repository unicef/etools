Development Environment Setup Instructions (OSX)
================================================

Setup Server
------------
Step 1. Check python version, it should be 2.7.x

```bash
$ python --version
Python 2.7.10
```

Step 2. Install Postgres with brew, create Postgres database, and run the Postgres upon startup:

```bash
$ brew install postgresql
```

In case of failing initdb during install, change the ownership of the postgres dir, and re-run postinstall to make initdb work:

```bash
$ sudo chown -R `whoami` /usr/local/var/postgres  
$ brew postinstall postgresql
```

If all went fine, start the service:

```bash
$ brew services start postgresql
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
# CREATE EXTENSION hstore;
# \q
```

Modifiy the base template so all newly created test databases will have hstore extension:

```bash
$ psql -d template1 -c 'CREATE EXTENSION hstore;'
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
$ pip install --upgrade pip  # cryptography install fails due to openssl problems in case of pip 7.x
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

You may need to drop and recreate the database to start from scratch:

```bash
$ dropdb -U postgres postgres
$ createdb -U postgres postgres
```

Then migrate the database and add the user:

```bash
$ source ~/.virtualenvs/env1/bin/activate
$ python manage.py migrate_schemas --fake-initial --noinput
$ python manage.py createsuperuser --username=etoolusr
```

Load Default Data
-----------------

Import the test data:

```bash
$ bzcat db_dumps/pg_backup1_27-07-16.bz2 | nice pg_restore --verbose -F c -d postgres
```

Assign the test country (UAT) to the user:

```bash
$ source ~/.virtualenvs/env1/bin/activate
$ python manage.py shell
Python 2.7.10 (default, Oct 23 2015, 19:19:21)

>>> from users.models import UserProfile, Country, Office, Section
>>> from django.contrib.auth.models import User
>>> user = User.objects.get(id=1)
>>> userp = UserProfile.objects.get(user=user)
>>> country=Country.objects.get(name='UAT')
>>> userp.country = country
>>> userp.country_override = country
>>> userp.save()
```

Run Server
----------

```bash
$ source ~/.virtualenvs/env1/bin/activate
$ export DATABASE_URL=postgis://postgres:password@localhost:5432/postgres
$ python EquiTrack/manage.py runserver 8080
```

Login to the Admin Portal using the 'etoolusr' user:

 ```bash
http://127.0.0.1:8080/admin/login/
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
