#### Running with Docker (SaaS Architecture)
The application is designed to run as a set of containers mirroring a production SaaS architecture. This setup includes:
- **Web**: The Flask web application.
- **Worker**: A Celery worker for processing large CSV uploads in the background.
- **Postgres**: A persistent database for user data, portfolios, and journal entries.
- **Redis**: A message broker for the task queue and result backend.

**Prerequisites:**
- Docker and Docker Compose installed on your machine.

**Steps:**
1.  Start all services:
    ```bash
    docker-compose up --build
    ```
2.  The application will be available at http://127.0.0.1:5000.
3.  To stop the services:
    ```bash
    docker-compose down
    ```

**Persistence:**
- Database data is persisted in a Docker volume `postgres_data`.
- Redis data is persisted in a Docker volume `redis_data`.
- Report metadata and logs are stored in the mounted `./instance` directory.
