FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Gunicorn command
CMD ["gunicorn", "--chdir", "/app", "--bind", "0.0.0.0:8000", "config.wsgi:application"]