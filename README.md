# Docker Setup for Lucro Django Project

This docker-compose setup provides a complete development environment with:
- **PostgreSQL**: Database service
- **Redis**: Cache and message broker for Celery
- **Django**: Web application server
- **Celery**: Task queue worker

## Prerequisites

- Docker and Docker Compose installed
- Port 8000 (Django), 5432 (PostgreSQL), and 6379 (Redis) available
- A `env` file in the projecct root

Create a `.env` file at the project root with any environment-specific variables. See `.env.example` for available options.

## Quick Start

### 1. Build and Start Services

```bash
docker-compose up -d
```

This will:
- Build the Docker image for your Django app
- Start PostgreSQL, Redis, Django app, and Celery worker
- Run migrations automatically
- Start the Django development server on `http://localhost:8000`

### 2. Verify Services

Check that all services are running:

```bash
docker-compose ps
```

### 3. Access Services

- **Django Web App**: http://localhost:8000
- **PostgreSQL**: `localhost:5432` (from your machine or container)
- **Redis**: `localhost:6379`


### 4. Making Requests

An auth token will be needed to access protected endpoints.  
You can obtain a token by creating a user and using the DRF token generation endpoint (detailed below).

Create a superuser:

```bash
docker-compose exec web python src/manage.py createsuperuser
```

You can use the Django admin interface at `http://localhost:8000/admin/` to manage users and tokens via the newly created superuser account.

Alternatively, you can obtain an auth token using the DRF token endpoint:

```bash
curl -X POST -d "username=yourusername&password=yourpassword" http://localhost:8000/api-token-auth/
```

This will return a JSON response with the token:

```json
{"token":"your_generated_token"}
```

Use this token in the `Authorization` header for subsequent API requests:

```bash
curl -H "Authorization: Token <your-token>" "http://localhost:8000/api/reports/account/acc_12345/summary/?start_date=2025-10-01&end_date=2025-10-31"
```
