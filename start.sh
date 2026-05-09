#!/bin/sh
mkdir -p /data/entries /data/images

exec gunicorn --bind 0.0.0.0:5001 --workers 2 --timeout 120 "app:create_app()"
