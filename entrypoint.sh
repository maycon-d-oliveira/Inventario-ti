#!/bin/sh
set -e

# Wait for PostgreSQL to be ready
until pg_isready -h db -p 5432 -U inventario > /dev/null 2>&1; do
  echo "Waiting for PostgreSQL to be ready..."
  sleep 2
done

echo "PostgreSQL is ready. Running migrations..."
# Run database migrations / schema creation within Flask app context
python - <<'PY'
import os
from app import create_app
app = create_app()
with app.app_context():
    from database import init_db
    init_db()
PY

# Start the Flask application
exec python app.py
