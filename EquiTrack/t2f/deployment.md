
eT2F setup
----------

1) Run all the migrations to create the db tables
2) To populate the db with test data, run the following command: 

```bash
$ source ~/.virtualenvs/env1/bin/activate
$ export DATABASE_URL=postgis://postgres:password@localhost:5432/postgres

$ python EquiTrack/manage.py import_exchange_rates Equitrack/t2f/data_xmls/GetCurrencyXrate_XML.xml
$ python EquiTrack/manage.py import_cost_assignments Equitrack/t2f/data_xmls/GetCostAssignment_XML.xml
$ python EquiTrack/manage.py load_initial_data
$ python EquiTrack/manage.py import_travel_agents Equitrack/t2f/data_xmls/GetTravelAgenciesInfo_XML.xml
```

### Generate invoices
To generate some invoices a travel has to be created and has to be sent for payment.
