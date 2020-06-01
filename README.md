# Flower Evolver Backend #

Flower Evolver backend, frontend can be found [here](https://github.com/cristianglezm/FlowerEvolver-frontend)

## Running ##

    * clone repository
    * pip install requirements.txt
    * configure SECRET_KEY inside app/settings.py [default ""]
    * configure origins inside singleton.py [default *]
    * Run following commands:
        * python manage.py db init
        * python manage.py db migrate
        * python manage.py db upgrade
        * python app.py

## Routes and Responses ##

* /api/flowers
create a new flower sending a empty POST, GET will get you:
```javascript
    {
        count: Number
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
