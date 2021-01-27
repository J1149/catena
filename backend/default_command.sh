#!/usr/bin/env bash
python manage.py collectstatic
gunicorn --access-logfile gunicorn.log --workers 3 --bind unix:/code/catena.sock backend.wsgi:application &
# daemon off -> run nginx in the foreground to stop docker from closing.
nginx -g 'daemon off;'