# Database

This directory handles all database-related operations for the application.

mongodb atlas cluster free tier 

database implementation for users is about to go through a refactor

- **crud.py**: Contains the core functions for Create, Read, Update, and Delete (CRUD) operations on the database. All interactions with the database models are handled in this file.
- **database.py**: Manages the database connection lifecycle. It establishes a connection to the MongoDB database when the application starts and closes it gracefully on shutdown.
- **schema.py**: Defines the Pydantic models that correspond to the database collections. These models are used for data validation, serialization, and ensuring data consistency.
- **example.db.schema.json**: Provides a JSON schema that defines the validation rules for the database collections. This can be used for automated validation and documentation.
- **.env**: Contains environment variables for the database, such as the connection string and database name. **Note:** This file should not be committed to version control.