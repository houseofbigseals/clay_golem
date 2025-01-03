# Clay golem
### Introduction
The simplest possible web interface for remote control
and automation of work with experimental stands of 
the O-125 laboratory. It can be launched both in the 
cloud and on a local machine, for example Raspberry Pi.
It does not have any protection during data transfer
or authorization mechanisms, so it is assumed that 
you are running the server STRICTLY on a laboratory 
VPN network. Tested only on Linux.

#### How it works
The central element of the entire system is the redis 
database, which stores all the current data about the 
state of the experimental setup, as well as data about 
the current state of the backend processes.

The frontend is implemented using the Flask framework, the bootstrap
library and the gunicorn wsgi server. gunicorn manages
the flask server processes, which draws a web page 
using bootstrap primitives. The frontend is completely
stateless, it simply renders the control interface and
the state of the devices using data from the database.
Due to this, you can run as many flask processes as you
like in parallel.

#### Installation way
To make system works, you have to install app STRICTLY in /opt/clay/clay_golem
This path is hardcoded inside app and if you change it, everything will fail.

#### Frontend
We are using AJAX polling from user browser to server 
to get updates from db without manual reloading web-page.
It is old method but very simple. May be in future we will
migrate to web-sockets technology.
All js scripts stored in flaskr/templates folder. They are very simple

#### Backend


#### Logging
Now logging works using python util, and all logs will come in /opt/clay/clay_golem/flaskr/logs folder.  
Every day script creates new files info_YYYY_MM_DD, error_YYYY_MM_DD, warning_YYYY_MM_DD etc.
This is to separate verbose logging like debug from error logs, those can be critical to find.

#### Data handling
We have two databases, redis and sqlite. Redis installed system-wide, sqlite lives in /opt/clay/clay_golem/flaskr/instance  
Redis stores only operational data, current parameters of each device. Different flask instances update their states and 
send info through redis. Also background tasks, spawned by flask, controlled by reading redis.
Experiment data stored in sqlite table, and we need to clean sqlite tables before each experiment.
Each device has own id, defined by hardware configuration file, and for each we have table named device_{id}_{data_type}. 
For each type of data that device handle, we have own small table.
Each row of that table is one measurement, and consists of num, date, time, value. Just it.  

We store data in sqlite in two situations: if user directly changed state of device and our flask instance registered it.
And if automation script made some operation - it writes data changing by itself.

#### Config and hardware configuration



### Installation
1. install python3, pip, venv;  
2. install redis [link](https://redis.io/docs/install/install-redis/install-redis-on-linux/)
3. ```sudo mkdir /opt/clay```
4. ```sudo chown -R <your_user>:<your_user> /opt/clay```
5. clone project from github to /opt/clay so it will be in /opt/clay/clay_golem
6. create new venv inside /opt/clay/clay_golem and activate it  
```python3 -m venv venv```   
then use ```source /opt/clay/clay_golem/venv/bin/activate```
7. install requirements via pip -r   
```pip install -r requirements.txt```
8. ```mkdir instance```  
and create or copy config.py with hardware configuration to  ./instance file 
9. manually copy systemd service files for 
   1. web-server with gunicorn wsgi
   ```sudo cp ./deploy/clay_golem.service /etc/systemd/system/clay_golem.service```
   2. rq-scheduler
   ```sudo cp ./deploy/clay_golem_scheduler.service /etc/systemd/system/clay_golem_scheduler.service```
   3. rq-workers (via template)
   ```sudo cp ./deploy/clay_golem_worker@.service /etc/systemd/system/clay_golem_worker@.service```
10. reload systemd ```sudo systemctl daemon-reload```
11. enable all needed services
    * ```sudo systemctl enable clay_golem_scheduler.service```
    * ```sudo systemctl enable clay_golem.service```
    * ```sudo systemctl enable clay_golem_worker@1.service```
    * ```sudo systemctl enable clay_golem_worker@2.service```
    * ```sudo systemctl enable clay_golem_worker@3.service```
    *  ... enable as many workers as you need (look at config.py to check your current num of rq workers)
12. allow selected app host and port in firewall if there is such

### Configuration
All hardware configuration, database, all app paths, 
network addresses stores in default flask config in same format
#### Logic of hardware handling
#### Logic of creating and handling rq tasks
#### config.py file 
#### gunicorn.conf.py

### How to start
All console commands related to app can be run with flask click wrapper to store 
unified config file and app context in all operations related to app
1. go to app folder, init venv
2. run ```flask --app flaskr init-db``` to create or clean existing db (if you need to fully remove all previous state of devices from redis)
3. run ```flask --app flaskr start-tasks``` to create rq-tasks corresponded to config
4. run ```flask --app flaskr start-workers``` 
5. run ```flask --app flaskr start-app``` 

### How to stop
1. go to app folder, init venv
2. run ```flask --app flaskr clear-queue``` to remove 
jobs of all types from rq queue
3. run ```flask --app flaskr stop-workers``` to stop all workers from systemd
4. run ```flask --app flaskr stop-app```

### How to change something in automation logic

### Uninstall
1. manually remove systemd services
2. manually remove app directory
3. uninstall redis using apt

