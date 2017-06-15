FROM mdillon/postgis:9.5

# Use this if there is a db dump file
# RUN mkdir -p /tmp/psql_data/
# COPY db1.bz2 /tmp/psql_data/

#COPY ./load_db_data.sh /docker-entrypoint-initdb.d/postgis.sh

EXPOSE 5432
CMD ["postgres"]