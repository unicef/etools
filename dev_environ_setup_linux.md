Development Environment Setup Instructions (Linux Ubuntu)
================================================

Setup Server
------------

Step 1. Install PostgreSQL and PostGIS, and Dev libraries

```bash
$ sudo apt-get update
$ sudo lsb_release -a   (copy ubuntu version number)
$ sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt (enter ubuntu version number)-pgdg main" >> /etc/apt/sources.list'
$ wget --quiet -O - http://apt.postgresql.org/pub/repos/apt/ACCC4CF8.asc | sudo apt-key add -
$ sudo apt-get update
$ sudo apt-get install postgresql-9.5-postgis-2.2 pgadmin3 postgresql-contrib-9.5
$ sudo apt-get install libpq-dev
```

Step 2. Connect to database

```bash
$ sudo -u postgres psql postgres
```

Step 3. Set Postgres user password to "postgres", and create PostGIS required extensions:

```bash
# alter user postgres with password 'postgres';
# CREATE EXTENSION postgis;
# CREATE EXTENSION postgis_topology;
# CREATE EXTENSION fuzzystrmatch;
# \q
```

Step 4. Install Redis

```bash
$ wget http://download.redis.io/redis-stable.tar.gz
$ tar xvzf redis-stable.tar.gz
$ cd redis-stable
$ sudo make install
$ make test
```

Step 5. Install git and clone eTools repository

```bash
$ sudo apt install git
$ git clone https://github.com/unicef/etools.git
```

* Replace URL with https://github.com/(your-username)/etools.git if working from a fork.

Step 6. Install latest pip, Python dev libraries, VirtualEnv, and VirtualEnvWrapper

```bash
$ sudo apt-get install python-pip python-dev build-essential
$ sudo pip install virtualenv
$ sudo pip install virtualenvwrapper
```

Step 7. Create Virtual Environment

```bash
$ mkdir ~/.virtualenvs
$ export WORKON_HOME=~/.virtualenvs
```

* Add `. /usr/local/bin/virtualenvwrapper.sh` to the end of ~/.bashrc

```bash
$ mkvirtualenv env1
```

* Making the virtual enviornment also activates it. But just in case it isn't, activate it with `workon env1`

Step 8. Install GDAL dependencies

```bash
$ sudo apt-get install libgdal-dev
$ export CPLUS_INCLUDE_PATH=/usr/include/gdal
$ export C_INCLUDE_PATH=/usr/include/gdal
```

Step 9. Install Cryptography dependencies

```bash
$ sudo apt-get install libffi-dev
$ sudp apt-get install libssl-dev
```

Step 10. Load Python packages

```bash
$ pip install -r path/to/etools/EquiTrack/requirements/base.txt
```

Step 11. Set environment variables:

```bash
$ export REDIS_URL=redis://localhost:6379/0
$ export DATABASE_URL=postgis://postgres:postgres@localhost:5432/postgres
```

Step 12. Connect to database and create required hstore extension

```bash
$ sudo -u postgres psql postgres
# CREATE EXTENSION hstore;
# \q
```

Step 13. Migrate database schemas and create database superuser

```bash
$ python path/to/etools/EquiTrack/manage.py migrate_schemas --fake-initial --noinput
$ python path/to/etools/EquiTrack/manage.py createsuperuser
```


Run Server
----------

```bash
$ workon env1
$ export DATABASE_URL=postgis://postgres:(your-password-here)@localhost:5432/postgres
$ python path/to/etools/EquiTrack/manage.py runserver 8080
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
* Set the Host to `localhost`
* In the Configuration make sure to add the environment variables again +
    * DEBUG=True
* Choose the python interpreter (The interpreter inside of the virtual environment)
* Choose a working Directory

Step 4:
* Quit Pycharm and restart it

Step 5:
* Run the server
* Go back to Edit Configurations
* Change the environment variable `DJANGO_SETTINGS_MODULE` to `EquiTrack.settings.local`
* Rerun the server

Resources
---------

https://www.digitalocean.com/community/tutorials/how-to-install-and-use-postgresql-on-ubuntu-14-04

https://trac.osgeo.org/postgis/wiki/UsersWikiPostGIS22UbuntuPGSQL95Apt

http://redis.io/topics/quickstart

http://roundhere.net/journal/virtualenv-ubuntu-12-10/
