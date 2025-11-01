import logging
import socket
import json
import uuid
import os
import time
import threading
from datetime import datetime
import random
import re
from typing import Optional


class TSLGConnection:
    """Управляет одним соединением с TSLG агентом"""

    def __init__(self, host: str, port: int, timeout: float):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.socket: Optional[socket.socket] = None
        self.created_at = time.time()

    def connect(self) -> bool:
        """Устанавливает соединение"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            self.created_at = time.time()
            return True
        except Exception:
            self.close()
            return False

    def send(self, data: bytes) -> bool:
        """Отправляет данные через соединение"""
        if not self.socket:
            return False

        try:
            self.socket.sendall(data)
            return True
        except Exception:
            self.close()
            return False

    def is_stale(self, ttl_ms: int) -> bool:
        """Проверяет, устарело ли соединение"""
        return (time.time() - self.created_at) * 1000 >= ttl_ms

    def close(self):
        """Закрывает соединение"""
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None


class TSLGBufferedSocketHandler(logging.Handler):
    """
    Обработчик логов с буферизацией и переподключением для TSLG.
    """

    def __init__(
        self,
        host: str,
        port: int,
        max_buffer_size: int = 500,
        flush_interval_ms: int = 100,
        connection_ttl_ms: int = 2000,
        reconnection_delay_ms: int = 2000,
        socket_timeout_ms: int = 5000,
        max_connection_attempts: int = 10
    ):
        super().__init__()
        self.host = host
        self.port = port
        self.max_buffer_size = max_buffer_size
        self.flush_interval_ms = flush_interval_ms
        self.connection_ttl_ms = connection_ttl_ms
        self.reconnection_delay_ms = reconnection_delay_ms
        self.socket_timeout_ms = socket_timeout_ms / 1000.0
        self.max_connection_attempts = max_connection_attempts

        self.buffer = []
        self.buffer_lock = threading.Lock()
        self.connection: Optional[TSLGConnection] = None
        self.connection_attempts = 0
        self._shutdown = False

        self._start_background_tasks()

    def _start_background_tasks(self):
        """Запускает фоновые задачи для отправки и поддержания соединения"""
        self.flush_thread = threading.Thread(
            target=self._flush_worker,
            daemon=True,
            name="TSLGFlushWorker"
        )
        self.health_thread = threading.Thread(
            target=self._health_check_worker,
            daemon=True,
            name="TSLGHealthWorker"
        )

        self.flush_thread.start()
        self.health_thread.start()

    def _get_connection(self) -> Optional[TSLGConnection]:
        """Возвращает валидное соединение, при необходимости создает новое"""
        if self.connection and not self.connection.is_stale(self.connection_ttl_ms):
            return self.connection

        if self.connection:
            self.connection.close()

        self.connection = TSLGConnection(
            self.host,
            self.port,
            self.socket_timeout_ms
        )

        if self.connection.connect():
            self.connection_attempts = 0
            return self.connection
        else:
            self.connection_attempts += 1
            self.connection = None
            return None

    def _send_batch(self, batch_data: list) -> bool:
        """Отправляет пачку логов"""
        if not batch_data:
            return True

        connection = self._get_connection()
        if not connection:
            return False

        log_data = '\n'.join(batch_data) + '\n'
        return connection.send(log_data.encode('utf-8'))

    def _flush_worker(self):
        """Фоновая задача для периодической отправки буфера"""
        while not self._shutdown:
            try:
                time.sleep(self.flush_interval_ms / 1000.0)
                self.flush()
            except Exception:
                pass

    def _health_check_worker(self):
        """Фоновая задача для поддержания соединения"""
        while not self._shutdown:
            try:
                self._get_connection()
                time.sleep(1.0)
            except Exception:
                pass

    def emit(self, record):
        """Обрабатывает запись лога"""
        if self._shutdown:
            return

        try:
            formatted_record = self.format(record)

            with self.buffer_lock:
                self.buffer.append(formatted_record)

                if len(self.buffer) >= self.max_buffer_size:
                    batch_to_send = self.buffer[:]
                    self.buffer = []
                    self._send_batch_async(batch_to_send)

        except Exception as e:
            self.handleError(record)

    def _send_batch_async(self, batch_data: list):
        """Асинхронно отправляет пачку логов"""
        def send_task():
            if not self._send_batch(batch_data):
                with self.buffer_lock:
                    self.buffer = batch_data + self.buffer

        threading.Thread(target=send_task, daemon=True).start()

    def flush(self):
        """Принудительно отправляет буфер"""
        with self.buffer_lock:
            if self.buffer:
                batch_to_send = self.buffer[:]
                self.buffer = []
                self._send_batch(batch_to_send)

    def close(self):
        """Корректно закрывает обработчик"""
        self._shutdown = True
        self.flush()
        if self.connection:
            self.connection.close()
        super().close()

class TSLGJSONLogFormatter(logging.Formatter):
    def __init__(self):
        super().__init__()

        self.app_name = os.getenv('APP_NAME', 'integration')
        self.ris_code = os.getenv('RIS_CODE', '1404')
        self.project_code = os.getenv('PROJECT_CODE', 'sum')

        self.namespace = os.getenv('KUBERNETES_NAMESPACE', 'default')
        self.pod_ip = os.getenv('POD_IP', '')
        self.node_name = os.getenv('NODE_NAME', '')
        self.pod_name = os.getenv('POD_NAME', '')

        self.tslg_client_version = os.getenv('TSLG_CLIENT_VERSION', '1.0.0')
        self.enable_trace_fields = os.getenv('TSLG_ENABLE_TRACE_FIELDS', 'true').lower() == 'true'
        self.enable_full_context = os.getenv('TSLG_ENABLE_FULL_CONTEXT', 'true').lower() == 'true'

        self.app_type = 'PYTHON'
        self.env_type = os.getenv('TSLG_ENV_TYPE', 'K8S')
        self.agr_type = 'TRACING'

    def format(self, record):
        log_data = {
            'eventId': str(uuid.uuid4()),
            'appName': self.app_name,
            'level': record.levelname,
            'text': self._format_message(record),
            'localTime': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
            'tslgClientVersion': self.tslg_client_version,
            'namespace': self.namespace,
            'risCode': self.ris_code,
            'projectCode': self.project_code,
            'appType': self.app_type,
            'envType': self.env_type,
            'agrType': self.agr_type,
            'loggerName': record.name,
            'threadName': record.threadName if hasattr(record, 'threadName') else str(record.thread),
            'callerClass': record.module,
            'callerMethod': record.funcName,
            'callerLine': record.lineno,
        }

        if self.pod_ip:
            log_data['podIp'] = self.pod_ip
        if self.node_name:
            log_data['nodeName'] = self.node_name
        if self.pod_name:
            log_data['podName'] = self.pod_name

        mdc = self._get_mdc_data(record)
        if mdc:
            log_data['mdc'] = mdc

        if record.exc_info:
            log_data['stack'] = self.formatException(record.exc_info)

        if self.enable_trace_fields:
            self._add_trace_fields(log_data, record)

        # Удаляем None значения
        log_data = {k: v for k, v in log_data.items() if v is not None}

        return json.dumps(log_data, ensure_ascii=False)

    def _format_message(self, record):
        """Форматирование основного сообщения"""
        message = record.getMessage()

        sanitize_enabled = os.getenv('TSLG_SANITIZE_SENSITIVE_DATA', 'true').lower() == 'true'
        if sanitize_enabled and message:
            message = self._sanitize_sensitive_data(message)

        return message

    def _sanitize_sensitive_data(self, text):
        """Улучшенная санитизация чувствительных данных"""
        if not text or not isinstance(text, str):
            return text

        # Паттерны для чувствительных данных
        patterns = {
            'password': r'("password"\s*:\s*")[^"]*(")',
            'token': r'("token"\s*:\s*")[^"]*(")',
            'authorization': r'(Authorization:\s*)[^\s]+',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        }

        sanitized_text = text
        for key, pattern in patterns.items():
            if key in ['password', 'token']:
                sanitized_text = re.sub(pattern, r'\1***\2', sanitized_text, flags=re.IGNORECASE)
            elif key == 'authorization':
                sanitized_text = re.sub(pattern, r'\1***', sanitized_text, flags=re.IGNORECASE)
            elif key == 'email':
                sanitized_text = re.sub(pattern, '***@***.***', sanitized_text)

        return sanitized_text

    def _get_mdc_data(self, record):
        """Получение MDC данных из record"""
        mdc = {}

        extra_fields = ['process', 'processName', 'pathname', 'filename']
        for field in extra_fields:
            if hasattr(record, field):
                mdc[field] = getattr(record, field)

        for key, value in record.__dict__.items():
            if key not in ['args', 'asctime', 'created', 'exc_info', 'exc_text',
                          'filename', 'funcName', 'levelname', 'levelno', 'lineno',
                          'module', 'msecs', 'message', 'msg', 'name', 'pathname',
                          'process', 'processName', 'relativeCreated', 'stack_info',
                          'thread', 'threadName'] and not key.startswith('_'):
                mdc[key] = str(value)

        return mdc if mdc else None

    def _add_trace_fields(self, log_data, record):
        """Добавление trace полей"""
        trace_fields = {}

        if not hasattr(record, 'traceId'):
            trace_fields['traceId'] = str(uuid.uuid4())

        if not hasattr(record, 'spanId'):
            trace_fields['spanId'] = str(uuid.uuid4())[:16]

        for field in ['traceId', 'spanId', 'parentSpanId', 'userId', 'logicTime']:
            value = getattr(record, field, None)
            if value is not None:
                trace_fields[field] = value

        if trace_fields:
            log_data.update(trace_fields)