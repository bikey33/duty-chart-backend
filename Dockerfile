FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app


# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create directories for static and media files
#RUN mkdir -p static media

# Collect static filesdoc
#RUN python app/manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "--chdir", "app", "--bind", "0.0.0.0:8000", "config.wsgi:application"] 