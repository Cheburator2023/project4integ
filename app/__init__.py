from flask import Flask, jsonify, request, render_template
from logging.config import dictConfig
from pathlib import Path
import os
import functools
import logging
from app.config import logging_level, logs_directory
from app.tslg_logging import TSLGBufferedSocketHandler, TSLGJSONLogFormatter

from requests.packages.urllib3.exceptions import InsecureRequestWarning
import requests
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

requests.get = functools.partial(requests.get, verify=False)
requests.post = functools.partial(requests.post, verify=False)
requests.put = functools.partial(requests.put, verify=False)

os.environ['PYTHONWARNINGS'] = 'ignore:Unverified HTTPS request'
UPLOAD_FOLDER = '/home/user/tmp'
NOT_ALLOWED_EXTENSIONS = {'exe', 'ppk'}

# Конфигурация логирования
log_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "logText": {
            "format": "[%(asctime)s] [%(process)d] [%(levelname)s] in %(module)s: %(message)s",
            "datefmt": "%d-%m-%Y %H:%M:%S"
        },
        "logJSON": {
            "()": "app.json_logging.JSONLogFormatter"
        },
        "tslgJSON": {
            "()": "app.tslg_logging.TSLGJSONLogFormatter"
        }
    },
    "handlers": {
        "wsgi": {
            "class": "logging.StreamHandler",
            "stream": "ext://flask.logging.wsgi_errors_stream",
            "formatter": "logText",
        },
        "tslg": {
            "class": "app.tslg_logging.TSLGBufferedSocketHandler",
            "host": os.getenv('TSLG_AGENT_HOST', 'tslg-agent-svc-main.dk1-sumd01-sumd-core.svc.cluster.local'),
            "port": int(os.getenv('TSLG_AGENT_PORT', '5170')),
            "max_buffer_size": int(os.getenv('TSLG_MAX_BUFFER_SIZE', '500')),
            "flush_interval_ms": int(os.getenv('TSLG_BUFFER_FLUSH_INTERVAL_MS', '100')),
            "connection_ttl_ms": int(os.getenv('TSLG_CONNECTION_TTL_MS', '2000')),
            "reconnection_delay_ms": int(os.getenv('TSLG_RECONNECTION_DELAY_MS', '2000')),
            "socket_timeout_ms": int(os.getenv('TSLG_SOCKET_TIMEOUT_MS', '5000')),
            "max_connection_attempts": int(os.getenv('TSLG_MAX_CONNECTION_ATTEMPTS', '10')),
            "formatter": "tslgJSON",
            "level": os.getenv('TSLG_LOG_LEVEL', 'INFO')
        }
    },
    "root": {
        "level": logging_level,
        "handlers": ["wsgi", "tslg"]
    },
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

logging.info("TSLG logging configured successfully")
logging.info(f"TSLG Agent: {os.getenv('TSLG_AGENT_HOST')}:{os.getenv('TSLG_AGENT_PORT')}")
logging.info(f"Buffer size: {os.getenv('TSLG_MAX_BUFFER_SIZE')}, Flush interval: {os.getenv('TSLG_BUFFER_FLUSH_INTERVAL_MS')}ms")

# To allow flask propagating exception even if debug is set to false on integration_services
app.config['PROPAGATE_EXCEPTIONS'] = True
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.before_first_request
def log_startup_message():
    logger = logging.getLogger(__name__)
    logger.info("Application started - TSLG test log")
    logger.info(f"Kubernetes: {os.getenv('POD_NAME')} on {os.getenv('NODE_NAME')}")

    try:
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.settimeout(5)
        test_socket.connect((os.getenv('TSLG_AGENT_HOST'), int(os.getenv('TSLG_AGENT_PORT', '5170'))))
        test_socket.close()
        logger.info("TSLG agent connection test: SUCCESS")
    except Exception as e:
        logger.error(f"TSLG agent connection test: FAILED - {e}")

from app import mlflow, bitbucket, nexus, jira, teamcity, upload, kafka_rest, s3_minio