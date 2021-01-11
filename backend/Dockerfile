FROM python:3.7.7-slim-buster

RUN apt-get update \
    # Necessary to be able to use psycopg2
    && apt-get install -y libpq-dev apt-transport-https gnupg \
    && apt-get install --no-install-recommends -y gcc  g++\
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    &&  mkdir code
# django
ENV PYTHONUNBUFFERED 1
ARG DATA_DIR

WORKDIR /code
COPY ./backend/requirements.txt /code/
RUN pip install -r requirements.txt 

ENV PYTHONPATH /code:$PYTHONPATH
ENV PAIPASS_BACKEND_SRC /code

COPY ./backend /code/

