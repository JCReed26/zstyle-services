# Database Breakdown 

MongoDB NOSQL database with json data 

example.db.schema.json - correlated to the validation of what is required to make an entry 
    For updates this can be passed with bypassDocumentValidation option in 'update operations'

crud.py - all interactions with database

database.py - connection that is open for life of the server to mongo db 

schema.py - layout for pydantic structure that matches storage json for auto DTO 