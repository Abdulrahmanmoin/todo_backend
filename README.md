# Todo Backend API

This is a FastAPI-based backend for the Todo application with authentication and task management capabilities.

## Features

- FastAPI framework with async support
- JWT-based authentication
- CRUD operations for tasks
- SQLModel ORM with PostgreSQL
- CORS configuration for frontend integration
- Proper error handling
- Containerized deployment support

## Project Structure

```
backend/
├── src/
│   ├── __init__.py
│   ├── main.py                 # Main FastAPI application
│   ├── config.py              # Configuration settings
│   ├── database.py            # Database connection and session management
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py           # User model definitions
│   │   └── task.py           # Task model definitions
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py           # Authentication endpoints
│   │   └── tasks.py          # Task management endpoints
│   └── utils/
│       ├── __init__.py
│       └── auth.py           # Authentication utilities (password hashing, JWT)
├── requirements.txt          # Python dependencies
└── README.md               # This file
```

## Setup Instructions

1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up environment variables:
   ```bash
   # Create .env file with the following variables:
   DATABASE_URL=postgresql+asyncpg://user:password@localhost/todo_db
   JWT_SECRET_KEY=your-super-secret-key-change-in-production
   JWT_ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
   ```

3. Run the application:
   ```bash
   uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   ```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register a new user
- `POST /api/v1/auth/login` - Login and get access token
- `GET /api/v1/auth/me` - Get current user info

### Tasks
- `GET /api/v1/tasks/` - Get all tasks for current user
- `POST /api/v1/tasks/` - Create a new task
- `GET /api/v1/tasks/{task_id}` - Get a specific task
- `PUT /api/v1/tasks/{task_id}` - Update a specific task
- `PATCH /api/v1/tasks/{task_id}/status` - Update task completion status
- `DELETE /api/v1/tasks/{task_id}` - Delete a specific task

### Health Check
- `GET /health` - Check API health status

## Development

To run the application in development mode:
```bash
python -m src.main
```

This will start the server with auto-reload enabled on port 8000.

## Documentation

The API includes automatic OpenAPI documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Docker Deployment

This backend can be deployed using Docker. A Dockerfile is included for easy containerization.

### Building the Docker Image

```bash
# From the backend directory
docker build -t todo-backend .
```

### Running with Docker

```bash
# Run the container
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://user:password@localhost/todo_db \
  -e JWT_SECRET_KEY=your-super-secret-key-change-in-production \
  -e JWT_ALGORITHM=HS256 \
  -e ACCESS_TOKEN_EXPIRE_MINUTES=30 \
  -e ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000 \
  todo-backend
```

### Deploying to Hugging Face Spaces

To deploy this backend on Hugging Face Spaces using Docker:

1. Create a Space with Docker Container type
2. Push your code to the Space repository
3. Ensure your Dockerfile is in the root of the backend directory
4. Configure the environment variables in the Space settings

The application will be available at port 8000 inside the container.