#!/bin/bash
docker run -d --name new_integration --log-driver json-file -h new_integration -ti -p 5777:5777 -v /var/run/docker.sock:/var/run/docker.sock -v /app/integration/user:/home/user -v /app/integration/integration:/home/user/integration --link redis integration:v2
 #gunicorn --workers 5 --timeout 90 --bind 0.0.0.0:5777 -c /home/user/gunicorn.config.py --log-level DEBUG wsgi:app
