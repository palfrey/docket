#!/bin/sh
FLASK_APP=docket.py FLASK_DEBUG=1 gunicorn docket:app --log-file - -b 0.0.0.0:5001 --reload
