# Stage 1: Build the Vue frontend
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python/Django Production Runtime
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DATABASE_DIR=/app/data
ENV DEBUG=False

WORKDIR /app

# Install dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy Python project files
COPY . /app/

# Copy the compiled static assets from Stage 1 into the Django app static dir
COPY --from=frontend-builder /app/budget/static/budget /app/budget/static/budget

# Gather all static files into staticfiles/ for Whitenoise serving
RUN python manage.py collectstatic --noinput

# Create the data folder for SQLite database persistence
RUN mkdir -p /app/data

EXPOSE 8000

# Run migrations and start gunicorn server
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn budget_project.wsgi:application --bind 0.0.0.0:8000"]
