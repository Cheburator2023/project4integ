from flask import Flask, jsonify, request, render_template
from logging.config import dictConfig
from pathlib import Path
# from flask_restful import reqparse
import requests
# import argparse
import os
import functools
from app.config import logging_level, logs_directory
# import time


from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

requests.get = functools.partial(requests.get, verify=False)
requests.post = functools.partial(requests.post, verify=False)
requests.put = functools.partial(requests.put, verify=False)

os.environ['PYTHONWARNINGS'] = 'ignore:Unverified HTTPS request'
UPLOAD_FOLDER = '/home/user/tmp'
NOT_ALLOWED_EXTENSIONS = {'exe', 'ppk'}

log_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "logText": {
            "format": "[%(asctime)s] [%(process)d] [%(levelname)s] in %(module)s: %(message)s",
            "datefmt": "%d-%m-%Y %H:%M:%S"
        },
        "logJSON": {
            "()": "app.logging.JSONLogFormatter"
        }
    },
    "handlers": {
        "wsgi": {
            "class": "logging.StreamHandler",
            "stream": "ext://flask.logging.wsgi_errors_stream",
            "formatter": "logText",
        }
    },
    "root": {"level": logging_level, "handlers": ["wsgi"]},
}
if logs_directory:
    logs_dir: Path = Path(logs_directory)
    if not logs_dir.exists():
        logs_dir.mkdir(parents=True)
    log_file_name: Path = logs_dir / Path("integration.log")
    handler_name = 'file'
    file_handler = {
        handler_name: {
            "class": "logging.FileHandler",
            "formatter": "logJSON",
            "filename": str(log_file_name),
        }
    }
    log_config["handlers"].update(file_handler)
    log_config["root"]["handlers"].append(handler_name)
dictConfig(log_config)
app = Flask(__name__)

# To allow flask propagating exception even if debug is set to false on integration_services
app.config['PROPAGATE_EXCEPTIONS'] = True
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

from app import mlflow, bitbucket, nexus, jira, teamcity, upload, kafka_rest, s3_minio
