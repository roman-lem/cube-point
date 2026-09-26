FROM python:3.13-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=wsgi

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000
# Database migrations are applied before start.
CMD ["sh", "-c", "flask db upgrade && exec gunicorn --bind 0.0.0.0:5000 --workers 2 wsgi:app"]
