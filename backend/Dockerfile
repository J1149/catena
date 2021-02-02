FROM python:3.7.7-slim-buster

RUN apt-get update \
    # Necessary to be able to use psycopg2
    && apt-get install -y libpq-dev apt-transport-https gnupg \
    # todo do we need c++?
    && apt-get install --no-install-recommends -y gcc  g++\
    && apt-get install --no-install-recommends -y nginx gettext-base \
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    &&  mkdir code
# django
ENV PYTHONUNBUFFERED 1
ARG DATA_DIR

WORKDIR /code
COPY ./backend/requirements.txt /code/
RUN pip install -r requirements.txt 

# nginx stuff
RUN rm -rf /etc/nginx/conf.d
COPY ./backend/nginx.conf /etc/nginx/nginx.conf.template
ARG BACKEND_HOST
ENV BACKEND_HOST=$BACKEND_HOST
ARG BACKEND_PORT
ENV BACKEND_PORT=$BACKEND_PORT
#RUN printf
RUN envsubst '${BACKEND_HOST}:${BACKEND_PORT}' < '/etc/nginx/nginx.conf.template' > '/etc/nginx/nginx.conf'
RUN cat /etc/nginx/nginx.conf

ENV PYTHONPATH /code:$PYTHONPATH
ENV PAIPASS_BACKEND_SRC /code

COPY ./backend /code/