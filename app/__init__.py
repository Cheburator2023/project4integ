from flask import Flask
import os
import functools
import logging
from app.logging_manager import LoggingManagerFactory

from requests.packages.urllib3.exceptions import InsecureRequestWarning
import requests
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

requests.get = functools.partial(requests.get, verify=False)
requests.post = functools.partial(requests.post, verify=False)
requests.put = functools.partial(requests.put, verify=False)

os.environ['PYTHONWARNINGS'] = 'ignore:Unverified HTTPS request'
UPLOAD_FOLDER = '/home/user/tmp'
NOT_ALLOWED_EXTENSIONS = {'exe', 'ppk'}

def create_app():
    """Фабрика для создания приложения Flask"""
    app = Flask(__name__)

    logging_manager = LoggingManagerFactory.create_from_env()
    root_logger = logging_manager.setup_logging()

    app.logging_manager = logging_manager

    app.config['PROPAGATE_EXCEPTIONS'] = True
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    app.logger.info("Application logging configured successfully")
    app.logger.info(f"Log level: {logging_manager.app_config.level}")
    app.logger.info(f"TSLG Agent: {logging_manager.tslg_config.host}:{logging_manager.tslg_config.port}")
    app.logger.info(f"TSLG Console Output: {logging_manager.tslg_config.console_output}")

    _register_blueprints(app)

    return app

def _register_blueprints(app):
    """Регистрирует все модули приложения"""
    from app import mlflow, bitbucket, nexus, jira, teamcity, upload, kafka_rest, s3_minio

app = create_app()

@app.teardown_appcontext
def shutdown_logging(exception=None):
    """Корректно останавливает логирование при завершении приложения"""
    if hasattr(app, 'logging_manager'):
        app.logging_manager.shutdown()