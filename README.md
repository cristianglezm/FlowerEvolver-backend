# Flower Evolver Backend #

Flower Evolver backend, frontend can be found [here](https://github.com/cristianglezm/FlowerEvolver-frontend)

## Running ##

* git clone https://github.com/cristianglezm/FlowerEvolver-backend
* cd FlowerEvolver-backend
* pip install requirements.txt
* change .env as needed

```
HOST=localhost
DB=flowerevolver
PASSWD='passwd'
USER=user
ENV=production | development
ORIGINS=*
SECRET_KEY='notreallyneeded'
LD_LIBRARY_PATH=/full/path/to/FlowerEvolver-backend/bin:$LD_LIBRARY_PATH
```

* Run following commands:
    - python manage.py db init
    - python manage.py db migrate
    - python manage.py db upgrade
    - python wsgi.py

## Routes and Responses ##

* /api/flowers

    create a new flower sending a empty POST, GET will get you:

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
