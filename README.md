
# Agent Connect Server

This project is a Python-based server that connects to and manages multiple AI agents. It provides a central backend for handling agent interactions, user authentication, and data persistence.

## Project Structure

- **/agents**: Contains the individual agent applications.
- **/database**: Manages database connections, schema definitions, and CRUD operations.
- **/deployment**: Holds deployment-related scripts and configurations.
- **/frontend**: Contains the user interface files for interacting with the agents.
- **/routers**: Defines the API routes and request handlers for the server.

## Running the Application

This application is built with FastAPI and can be run with uvicorn.

### Prerequisites

- Python 3.11+
- pip

### Steps

1. **Install Dependencies**:

   From the root directory, run the following command to install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Server**:

   From the root directory, run the following command to start the server:

   ```bash
   uvicorn main:app --reload
   ```

   This will start the backend server at `http://localhost:8000`.
