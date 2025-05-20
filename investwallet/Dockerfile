FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/
RUN apt update && \
    apt install -y libpq-dev gcc musl-dev libffi-dev && \
    pip install --upgrade pip && pip install -r requirements.txt

COPY . /app/

CMD ["sh", "-c", "sleep 10 && python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]