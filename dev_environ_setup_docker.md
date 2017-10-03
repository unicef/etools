# Development Environment Setup Instructions (Docker)

## Requirements

 * Docker - https://docs.docker.com/engine/installation/
 * Git - https://www.git-scm.com/downloads


## Clone

```bash
$ git clone https://github.com/unicef/etools.git
```

Replace URL with https://github.com/(your-username)/etools.git if working from a fork.


## Setup Database

### 1. Start Database Service

```bash
$ docker-compose -f docker-compose_dev.yml up -d db
```

### 2. Get Database IP Address

```bash
$ docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' master_db_1
```

### 3. Load Data

```bash
$ bzcat <path/to/dg-dump.bz2> | pg_restore -h <ip-address> -U postgres -F t -d etools
```

**Note:**
 * Loading of data takes a while, so be patient.
 * You can ignore the `pg_pool*` errors.
 * Password is `password`


## Start Other Services

```bash
$ docker-compose -f docker-compose_dev.yml up -d
```

Drop the `-d` option if you want to have the processes run in the foreground and logging to be in the terminal.


You should be all set to access the application via your browser at [http://localhost:8000](http://localhost:8000)


## Useful Commands

When developing the following commands, may be helpful.

### Access Web Container

```bash
$ docker exec -it master_web_1 bash
```

Do this step first, which allows you to run django commands in the right environment


### Create User

If you need a user account to login to the application.

First access the web container, then;

```bash
$ python manage.py createsuperuser
```

### Database Migration Command

First access the web container, then;

```bash
$ python manage.py migrate_schemas
```

### Run Tests

First access the web container, then;

```bash
$ ./runtests.sh
```

### Update Requirements

First access the web container, then run the pip install command

```bash
$ pip install -r requirements/local.txt
```

**Note:** This only updates that container instance. You will want to update the docker image as well, so worker and beater have the same requirements.

A few steps to update the images.

#### 1. Stop any running containers

```bash
$ docker-compose -f docker-compose_dev.yml stop web worker beater
```

#### 2. Remove containers and images

```bash
$ docker-compose -f docker-compose_dev.yml rm web worker beater
$ docker rmi unicef/equitrack:etools master_worker:latest master_beater:latest
```

#### 3. Restart containers

```bash
$ docker-compose -f docker-compose_dev.yml up -d
```

**TODO:** Create a base image, that has necessary libraries installed etc, leaving the last layer to have the command to install requirements. Would make updating of requirements quicker.

### Restart Service

```bash
$ docker-compose -f docker-compose_dev.yml restart beater
```

### Clearing Cached Files

Periodically you may need to clear cached python files

```bash
find . -iname "*.pyc" -exec rm -f {} \;
```
