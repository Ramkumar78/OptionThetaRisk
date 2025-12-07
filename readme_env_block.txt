**Configuration (.env):**
Create a `.env` file in the root directory to configure the services.
```bash
POSTGRES_USER=user
POSTGRES_PASSWORD=securepassword
POSTGRES_DB=tradeauditor
SECRET_KEY=really-long-random-string
# Optional: Enable S3 Storage
# AWS_ACCESS_KEY_ID=your_key
# AWS_SECRET_ACCESS_KEY=your_secret
# S3_BUCKET_NAME=your_bucket
# AWS_REGION=us-east-1
```
The application will automatically switch to S3 storage for uploads and reports if `S3_BUCKET_NAME` is defined. Otherwise, it falls back to database storage (Postgres).
