import logging
import socket
import json
import uuid
import os
import time
import threading
from datetime import datetime
from queue import Queue, Empty
import random

class TSLGBufferedSocketHandler(logging.Handler):
    def __init__(self, host, port, max_buffer_size=500, flush_interval_ms=100,
                 connection_ttl_ms=2000, reconnection_delay_ms=2000,
                 socket_timeout_ms=5000, max_connection_attempts=10):
        super().__init__()
        self.host = host
        self.port = port
        self.max_buffer_size = max_buffer_size
        self.flush_interval_ms = flush_interval_ms
        self.connection_ttl_ms = connection_ttl_ms
        self.reconnection_delay_ms = reconnection_delay_ms
        self.socket_timeout_ms = socket_timeout_ms
        self.max_connection_attempts = max_connection_attempts

        self.buffer = []
        self.buffer_lock = threading.Lock()
        self.socket = None
        self.connection_start_time = 0
        self.connection_attempts = 0

        self.flush_thread = threading.Thread(target=self._flush_worker, daemon=True)
        self.flush_thread.start()

    def _sanitize_data(self, data):
        """Санитизация чувствительных данных"""
        sanitize_enabled = os.getenv('TSLG_SANITIZE_SENSITIVE_DATA', 'true').lower() == 'true'
        sanitize_percentage = int(os.getenv('TSLG_SANITIZE_PERCENTAGE', '60'))

        if not sanitize_enabled:
            return data

        if isinstance(data, str) and data.strip():
            chars = list(data)
            num_to_sanitize = int(len(chars) * sanitize_percentage / 100)
            if num_to_sanitize > 0:
                indices = random.sample(range(len(chars)), min(num_to_sanitize, len(chars)))
                for idx in indices:
                    chars[idx] = '*'
                return ''.join(chars)
        return data

    def _create_socket(self):
        """Создание нового сокет-соединения"""
        try:
            if self.socket:
                self.socket.close()

            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.socket_timeout_ms / 1000.0)
            self.socket.connect((self.host, self.port))
            self.connection_start_time = time.time()
            self.connection_attempts = 0
            return True
        except Exception as e:
            self.connection_attempts += 1
            if self.connection_attempts >= self.max_connection_attempts:
                self.handleError(f"Max connection attempts reached: {e}")
            return False

    def _ensure_connection(self):
        """Проверка и восстановление соединения"""
        current_time = time.time()
        connection_age = (current_time - self.connection_start_time) * 1000

        if (not self.socket or
            connection_age >= self.connection_ttl_ms or
            self.connection_attempts > 0):

            if not self._create_socket():
                time.sleep(self.reconnection_delay_ms / 1000.0)
                return self._create_socket()

        return self.socket is not None

    def _send_batch(self, batch_data):
        """Отправка пачки логов"""
        if not batch_data:
            return

        try:
            if not self._ensure_connection():
                return

            log_lines = [json.dumps(record) for record in batch_data]
            log_data = '\n'.join(log_lines) + '\n'

            self.socket.sendall(log_data.encode('utf-8'))

        except Exception as e:
            self.handleError(f"Error sending log batch: {e}")
            time.sleep(self.reconnection_delay_ms / 1000.0)
            self._create_socket()

    def _flush_worker(self):
        """Фоновая задача для периодической отправки буфера"""
        while True:
            time.sleep(self.flush_interval_ms / 1000.0)
            self.flush()

    def emit(self, record):
        """Обработка новой записи лога"""
        try:
            formatted_record = self.format(record)

            with self.buffer_lock:
                self.buffer.append(formatted_record)

                if len(self.buffer) >= self.max_buffer_size:
                    batch_to_send = self.buffer[:]
                    self.buffer = []
                    threading.Thread(target=self._send_batch, args=(batch_to_send,), daemon=True).start()

        except Exception as e:
            self.handleError(record)

    def flush(self):
        """Принудительная отправка буфера"""
        with self.buffer_lock:
            if self.buffer:
                batch_to_send = self.buffer[:]
                self.buffer = []
                threading.Thread(target=self._send_batch, args=(batch_to_send,), daemon=True).start()

    def close(self):
        """Закрытие обработчика"""
        self.flush()
        if self.socket:
            self.socket.close()
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
        self.env_type = 'KUBERNETES'
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
            'levelInt': record.levelno,
            'loggerName': record.name,
            'threadName': record.threadName if hasattr(record, 'threadName') else str(record.thread),
            'callerClass': record.module,
            'callerMethod': record.funcName,
            'callerLine': record.lineno,
        }

        tec_data = {}
        if self.pod_ip:
            tec_data['podIp'] = self.pod_ip
        if self.node_name:
            tec_data['nodeName'] = self.node_name
        if self.pod_name:
            tec_data['podName'] = self.pod_name

        if tec_data:
            log_data['tec'] = tec_data

        mdc = self._get_mdc_data(record)
        if mdc:
            log_data['mdc'] = mdc

        if record.exc_info:
            log_data['stack'] = self.formatException(record.exc_info)

        if self.enable_trace_fields:
            self._add_trace_fields(log_data, record)

        return log_data

    def _format_message(self, record):
        """Форматирование основного сообщения"""
        message = record.getMessage()

        sanitize_enabled = os.getenv('TSLG_SANITIZE_SENSITIVE_DATA', 'true').lower() == 'true'
        if sanitize_enabled and message:
            sanitize_percentage = int(os.getenv('TSLG_SANITIZE_PERCENTAGE', '60'))
            chars = list(message)
            num_to_sanitize = int(len(chars) * sanitize_percentage / 100)
            if num_to_sanitize > 0:
                indices = random.sample(range(len(chars)), min(num_to_sanitize, len(chars)))
                for idx in indices:
                    chars[idx] = '*'
                message = ''.join(chars)

        return message

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
            if hasattr(record, field):
                trace_fields[field] = getattr(record, field)

        if trace_fields:
            log_data.update(trace_fields)