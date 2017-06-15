#!/bin/bash
set -e

# Perform all actions as $POSTGRES_USER
export PGUSER="$POSTGRES_USER"

# Create the 'template_postgis' template db
"${psql[@]}" <<- 'EOSQL'
  CREATE DATABASE template_postgis;
  UPDATE pg_database SET datistemplate = TRUE WHERE datname = 'template_postgis';
EOSQL

# Load PostGIS into both template_database and $POSTGRES_DB
for DB in template_postgis "$POSTGRES_DB"; do
	echo "Loading PostGIS extensions into $DB"
	"${psql[@]}" --dbname="$DB" <<-'EOSQL'
		CREATE EXTENSION IF NOT EXISTS postgis;
		CREATE EXTENSION IF NOT EXISTS postgis_topology;
		CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
		CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder;
		CREATE EXTENSION IF NOT EXISTS hstore;
EOSQL

done

echo "*** CREATING DATABASE ***"

# create default database
"${psql[@]}" <<- 'EOSQL'
    DROP ROLE IF EXISTS etoolusr;
    CREATE ROLE etoolusr WITH superuser login;
    CREATE DATABASE etools;
    GRANT ALL PRIVILEGES ON DATABASE etools TO etoolusr;
EOSQL

# Use this if there is a db dump file
# echo "*** UPDATING DATABASE ***"
# export DB_DUMP_LOCATION=/tmp/psql_data/db1.bz2
#
# bzcat $DB_DUMP_LOCATION | nice pg_restore --verbose  -U etoolusr -F t -d etools

echo "*** DATABASE CREATED! ***"