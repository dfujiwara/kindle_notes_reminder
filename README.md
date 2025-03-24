# FastAPI Application

A sample FastAPI application with a basic setup.

## Features

- FastAPI framework with async support
- CORS middleware configured
- Health check endpoint
- Basic project structure
- Uses `uv` for fast, reliable Python package management

## Setup

1. Install uv (if not already installed):
```bash
pip install uv
```

2. Create and activate a virtual environment:
```bash
uv venv
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate  # On Windows
```

3. Install dependencies:
```bash
uv pip install -r requirements.txt
```

4. Run the application:
```bash
python main.py
```

Or alternatively:
```bash
uvicorn main:app --reload
```

The application will be available at http://localhost:8000

## API Documentation

Once the application is running, you can access:
- Interactive API documentation (Swagger UI) at http://localhost:8000/docs
- Alternative API documentation (ReDoc) at http://localhost:8000/redoc

## Endpoints

- `GET /`: Welcome message
- `GET /health`: Health check endpoint

## Package Management

To add new packages:
```bash
uv pip install package_name
uv pip freeze > requirements.txt
```
