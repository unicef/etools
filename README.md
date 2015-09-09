EquiTrack
=========

[![Circle CI](https://circleci.com/gh/UNICEFLebanonInnovation/EquiTrack/tree/develop.svg?style=svg)](https://circleci.com/gh/UNICEFLebanonInnovation/EquiTrack/tree/develop)

**Monitoring and Tracking Results for Children**



**What does it do?**

* Create and manage partnerships in a centralized and online database
* Attributing and tracking partnerships against multitude of Result Structures, Donors, Grants, Geographical locations and Gateways
* An online repository of PCA documentation accessible anywhere
* Custom reports generation to Excel, Google Earth (KML) and Shapefile (GIS)
* Monitors partnerships with standard indicators against set targets
* Dynamic Dashboard for Analysis and tracking results against global targets
* Convergence and Coverage analysis
* Interactive mapping of partner activities and locations

PCA Input

1. Add new PCA - can be multi-sector, with attributes: Status, Start and End Date, Budget, Implementing Partner NGO, Locations where it will be implemented, the Goals it is fulfilling, Target Number of Beneficiaries, Intermediate Results, WBS, RRP Outputs, PCA Files, Grants and Donors, etc.
2. Edit PCA - can add new attributes or remove existing ones.
3. Delete PCA - a PCA can be deleted, unless the implementation has started. In that case, its status can be set to "canceled".
4. Filtering of PCAs - is one of the main utilities of the tool, through which one can filter PCAs through one or more conditions, e.g.: by Sector, Indicator, Implementing Partner, CCC as well as through a more advanced filtering of attributes like, budget, locations, grant, start and end dates etc. , and export the results in excel and many other formats.

Result Structure Setup

1. RRP (Regional Response Plan) - belongs to a sector, and is a standardized description of UNICEF's outputs in emergencies.
2. CCC - How a PCA is contributing to a CCC.
3. Indicator - expressed through one (or more Units) and a target number of the corresponding unit. The automatic calculation of shortfall and progress towards target for all indicators, as PCAs are programmed and implemented, is the core feature of the system.
4. Units - add/edit/remove unit types, e.g. schools, children, women etc. (generally representing beneficiaries or points of interest where activities of PCAs happen or are about)
5. Activities - generic activities that happen in various PCAs, e.g. training, distribution of water tanks etc.
6. Intermediate Results, WBS Activity - correspond to a particular sector, with an Intermediate Result having many WBS (work breakdown structure) Activities

Administrative Data

1. Manage Sectors - UNICEF Sectors can be added, edited or removed (unless the sector has CCCs and other data that it is attributed with)
2. Add administrative data about country - 3 administrative levels are supported: Governorate, District, Cadastral
3. Add gateways (locations) - these represent schools, health centers and other generic locations where activities happen.
4. Partners - Partners can be added and assigned to PCAs.
5. Donors - donors can be added.
6. Grants - can be added and identified uniquely through grant reference numbers.

Dashboard - Visualization of cumulative (i.e. data from all PCAs) current and shortfall target levels, categorized by sector, 
Map - a web-based public map with bubbles, representing PCAs, which are clustered depending on zoom level and categorized through sector, indicator and partner organization.


**Installing the application locally on Mac**

1.  Checkout the develop branch of the git repository
> $ `git clone https://github.com/UNICEFLebanonInnovation/EquiTrack [loc_folder]`

2. Navigate to the parent folder
> $ `cd [loc_folder]`

3. Install Docker for Mac OSX
> * Download and Install from:  [https://www.docker.com/toolbox]
> * Make sure that your system supports Docker

4. Create the Docker machine
> $`docker-machine create --driver virtualbox eq`
>> (eq is the name of the virtual machine)

5. Bring in the environment variables from the docker vm
> $`eval "$(docker-machine env eq)"`

6. Spin up all containers and connect them
> $`docker-compose up -d`
>> (-d runs the containers deamonized - in the backroud)

7. Set up the database
> `docker run -it --link [LOC_FOLDER]_db_1:postgres --rm postgres sh`
> `psql -h "$POSTGRES_PORT_5432_TCP_ADDR" -p "$POSTGRES_PORT_5432_TCP_PORT" -U postgres`
> Once connected to the db:
> \#`CREATE EXTENSION postgis;`
> \#`CREATE EXTENSION postgis_topology;`
> \#`exit`

8. Make the apporpriate migrations 
> docker exec -it [LOC_FOLDER]_web_1 python equitrack/manage.py syncdb --migrate
> docker exec -it [LOC_FOLDER]_web_1 python equitrack/manage.py migrate

9. Find out the running docker machine’s ip address and navigate to it on port 8080
> $`docker-machine ip eq`

**Bring in backed up data or faux data from backup.sq**

1. Download faux data from [here](https://example.com/link_to_come)
> unpack the data file at `[DOWNLOAD_PATH]/backup.sql`

2. Get the data into the running database container by spinning up another container and linking it to the running db container.
>  $`docker run -it --link [LOC_FOLDER]_db_1:postgres -v [DOWNLOAD_PATH]:/sqlbackup --rm postgres sh`
>> (notice [LOC_FOLDER] is the name of the folder that you originally checked out the git repo to.)

3. Once the container is started, load the new data in:
> \# `psql -h "$POSTGRES_PORT_5432_TCP_ADDR" -p "$POSTGRES_PORT_5432_TCP_PORT" -U postgres < /sqlbackup/backup.sql`


> enter db password


> after the command executes exit out of the container


> \# `exit`



**The process**

![image](/screenshots/PCA_process.jpg "PCA Process")

**Screenshots**


PCA Management:

![PCA list](/screenshots/equitrack_pcas.png "List of PCAs")


Mapping of partner activities:

![PCA map](/screenshots/equitrack_map.png "Map of PCAs")


