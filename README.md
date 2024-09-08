# Flower Evolver Backend #

[![CI](https://github.com/cristianglezm/FlowerEvolver-backend/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/cristianglezm/FlowerEvolver-backend/actions/workflows/ci.yml)

Flower Evolver backend, frontend can be found [here](https://github.com/cristianglezm/FlowerEvolver-frontend)

## Running local ##

* git clone https://github.com/cristianglezm/FlowerEvolver-backend
* cd FlowerEvolver-backend
* pip install -r requirements.txt
* change .env as needed (use the absolute path for LD_LIBRARY_PATH)

```
HOST=localhost
DB=flowerevolver
PASSWD='passwd'
USER=user
ENV=production | development
ORIGINS=*
FLOWER_LIMIT=5000
SECRET_KEY='notreallyneeded'
LD_LIBRARY_PATH=./bin:$LD_LIBRARY_PATH
```

* Run following commands:
    - export FLASK_APP=FlowerEvolver.py
    - flask db init
    - flask db migrate
    - flask db upgrade
    - flask run

## Running docker ##

I recommend using the compose file from [frontend](https://github.com/cristianglezm/FlowerEvolver-frontend.git)
read the README-docker.md in [frontend](https://github.com/cristianglezm/FlowerEvolver-frontend.git) repo for how to.

The Alpine version needs to download some repositories(private for now) to build the executables,
the Ubuntu version has them inside the bin folder with the Windows executables.

If you want to use the alpine version you will need to pull the image from this 
[repo](https://hub.docker.com/repository/docker/cristianglezm/fe) and change the env variables as needed.

Before running the script to build the image, change the .env variables if you need to.

* build image (alpine or ubuntu)
    * sh build_docker.sh "alpine"
    * sh build_docker.sh "ubuntu"
* pull image (alpine(300MB) or ubuntu(800MB))
    * docker pull cristianglezm/fe:backend-alpine-dev
    * docker pull cristianglezm/fe:backend-ubuntu-dev
* docker run -dp 5000:5000 -v generated:/app/generated -v migrations:/app/migrations \ 
    -v db:/app/db cristianglezm/fe:backend-alpine-dev --env-file .env --hostname backend
* browse to http://localhost:5000/api/flowers to get a list of flowers.
    (use webtools to send request, a rest client or the frontend website.)

## Routes and Responses ##

* /api/flowers

     POST 

     create a new flower sending a POST with an empty json
     or a flower genome to share it (check generated/1.json).

     GET

```javascript
    {
        count: Number,
        flowers:[{ id: Number, genome:String, image:String}, ...],
    }
```

* /api/flowers/:id

    GET

```javascript
    {
        id: Number, 
        genome:String, 
        image:String
    }
```
* /api/flowers?count=1

    GET

```javasript
    {
        "count":0
    }
```

* /api/mutations

    POST send

```javascript
   {original:Number}
```
    GET

```javascript
    {
        count: Number,
        mutations[{id: Number, original: Number}, ...]
    }
```
* /api/mutations/:original

    GET

```javascript
    {[
        {id: Number, genome: String, image: String},
        ...
    ]}
```
* /api/mutations?count=1

    GET

```javasript
    {
        "count":0
    }
```

* /api/ancestors

    POST send

```javascript
   {
      father: Number,
      mother: Number
   }
```
    GET

```javascript
    {
        count: Number,
        ancestors:[{id:Number, father: Number, mother: Number}, ...]
    }
```

* /api/ancestors?count=1

    GET

```javasript
    {
        "count":0
    }
```

* /api/ancestors/:father

    GET

```javascript
    {[
        {id: Number, genome: String, image: String},
        ...
    ]}
```
* /api/ancestors/:father/:mother

    GET

```javascript
    {[
        {id: Number, genome: String, image: String},
        ...
    ]}
```
