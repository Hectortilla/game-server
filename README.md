# Game Server

Scalable server for realtime multiplayer videogames.

Event driven networking using twisted with an ORM layer based on Django.

Stateless server for scalability purposes.

It uses redis for fast communication between different server instances.

The intention of this server is to be used as a template, a barebone structure for your specific needs.

## Set up with docker

You need to have Docker and docker-compose  installed in you system
Under this same directory:
  
#### Build the image
    docker build -f docker/Dockerfile -t game-server .
      
#### If you do not want to rebuild the image every time you change the source code
Uncomment the 'volumes' section in the docker-compose.yml replacing </path/to/app/subdir> with your actual app subdirectory directory to the actual /app/<subdir>
    
    
#### Run the docker-compose
    docker-compose -f docker/docker-compose.yml up

#### Migrate
First time you run it, you are going to have to migrate the schema

    docker exec -it docker_snap_1 bash (if container already running)
    OR
    docker run -it --network docker_default game-server bash (if not running yet)
    
    ./manage.py migrate
    invoke createsuperuser
    ./manage.py loaddata </path/to/fixtures>

___

## Set up locally

#### install at least python3.6 and -dev

	sudo apt-get install python3.6
	sudo apt-get install python3.6-dev
	sudo apt-get install build-essential libssl-dev libffi-dev

#### Create virtual environment & activate it
	virtualenv </path/to/virt/environ>
	source </path/to/virt/environ/bin/activate>

#### Install pip-tools & its extra requirements
	pip install pip-tools

#### Install mysql-server & python-dev
	sudo apt-get install mysql-server
	sudo apt-get install libmysqlclient-dev

#### Install redis
    sudo apt-get install redis-server

#### Compile requirements.in & install the generated requirements.txt
	pip-compile requirements.in
	(if you have problems with pip-compile maybe downgrade pip: pip install --upgrade pip==18.1)
	pip install -r requirements.txt

#### Create environment file with the word 'development' on it
	echo "development" > environment

#### Migrations
First create a user in your db U: dev P: dev
     
     mysql -u root -p (if you cannot log in: https://stackoverflow.com/questions/41645309/mysql-error-access-denied-for-user-rootlocalhost)
     CREATE USER 'dev'@'localhost' IDENTIFIED BY 'dev';
     GRANT ALL PRIVILEGES ON *.* TO 'dev'@'localhost';
     invoke createdatabase
    ./manage.py migrate
    ./manage.py loaddata </path/to/fixtures>

#### run server
    python -m twisted game-server

#### run admin
    ./manage.py runserver

## TODOs

- [ ] Proper matchmaking
- [ ] Implement UDP message order and receive confirmation
- [ ] Optimize messages length (concatenate props, transform to bytes, etc...)
- [ ] Protobuf
- [ ] Anything else to fit your videogame, this is a template for all your needs. 
