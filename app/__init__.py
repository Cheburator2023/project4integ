from flask import Flask, jsonify, request, render_template
from logging.config import dictConfig
from pathlib import Path
import queue
from logging.handlers import QueueHandler, QueueListener
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

log_queue = queue.Queue(maxsize=10000)

tslg_handler = TSLGBufferedSocketHandler(
    host=os.getenv('TSLG_AGENT_HOST', 'tslg-agent-svc-main.dk1-sumd01-sumd-core.svc.cluster.local'),
    port=int(os.getenv('TSLG_AGENT_PORT', '5170')),
    max_buffer_size=int(os.getenv('TSLG_MAX_BUFFER_SIZE', '500')),
    flush_interval_ms=int(os.getenv('TSLG_BUFFER_FLUSH_INTERVAL_MS', '100')),
    connection_ttl_ms=int(os.getenv('TSLG_CONNECTION_TTL_MS', '2000')),
    reconnection_delay_ms=int(os.getenv('TSLG_RECONNECTION_DELAY_MS', '2000')),
    socket_timeout_ms=int(os.getenv('TSLG_SOCKET_TIMEOUT_MS', '5000')),
    max_connection_attempts=int(os.getenv('TSLG_MAX_CONNECTION_ATTEMPTS', '10'))
)

# Устанавливаем уровень логирования из env
tslg_log_level = os.getenv('TSLG_LOG_LEVEL', 'info').upper()
tslg_handler.setLevel(getattr(logging, tslg_log_level, logging.INFO))

tslg_formatter = TSLGJSONLogFormatter()
tslg_handler.setFormatter(tslg_formatter)

queue_listener = QueueListener(log_queue, tslg_handler)
queue_listener.start()

root_logger = logging.getLogger()
queue_handler = QueueHandler(log_queue)
root_logger.addHandler(queue_handler)

# Добавляем TSLG handler напрямую к root logger для гарантированной доставки
if os.getenv('TSLG_CONSOLE_OUTPUT', 'true').lower() == 'true':
    root_logger.addHandler(tslg_handler)

app = Flask(__name__)

# To allow flask propagating exception even if debug is set to false on integration_services
app.config['PROPAGATE_EXCEPTIONS'] = True
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

from app import mlflow, bitbucket, nexus, jira, teamcity, upload, kafka_rest, s3_minio
