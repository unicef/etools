
eT2F setup
----------

1) Run all the migrations to create the db tables
2) To populate the db with test data, run the following command: 

```bash
$ source ~/.virtualenvs/env1/bin/activate
$ export DATABASE_URL=postgis://postgres:password@localhost:5432/postgres
$ python EquiTrack/manage.py et2f_init
```