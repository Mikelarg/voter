FROM python:3.7-alpine

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=voter.docker_settings

RUN apk update \
    && apk add postgresql-dev gcc python3-dev musl-dev

RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY entrypoint.sh .

COPY . .

ENTRYPOINT ["/app/entrypoint.sh"]