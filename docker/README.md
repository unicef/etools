eTools DataMart Docker images
=============================

[![](https://images.microbadger.com/badges/version/unicef/etools.svg)](https://microbadger.com/images/unicef/etools)

To build docker image simply cd in `docker` directory and run 

    make build
    
default settings are for production ready environment, check `run` target in 
the `Makefile` to see how to run the container with debug/less secure configuration

Image provides following services:

    - etools   
    - celery workers
    - celery beat

