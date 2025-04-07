#!/bin/sh

exec poetry run gunicorn --bind 0.0.0.0:${PORT:-8080} app:app --log-level debug
