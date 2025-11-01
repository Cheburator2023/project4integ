from dataclasses import dataclass
from pathlib import Path
import os
from typing import Optional, Dict, Any
from app.config import logging_level, logs_directory


@dataclass
class TSLGConfig:
    """Конфигурация TSLG соединения"""
    host: str
    port: int
    max_buffer_size: int
    flush_interval_ms: int
    connection_ttl_ms: int
    reconnection_delay_ms: int
    socket_timeout_ms: int
    max_connection_attempts: int
    log_level: str
    console_output: bool

    @classmethod
    def from_env(cls) -> 'TSLGConfig':
        return cls(
            host=os.getenv('TSLG_AGENT_HOST', 'tslg-agent-svc-main.dk1-sumd01-sumd-core.svc.cluster.local'),
            port=int(os.getenv('TSLG_AGENT_PORT', '5170')),
            max_buffer_size=int(os.getenv('TSLG_MAX_BUFFER_SIZE', '500')),
            flush_interval_ms=int(os.getenv('TSLG_BUFFER_FLUSH_INTERVAL_MS', '100')),
            connection_ttl_ms=int(os.getenv('TSLG_CONNECTION_TTL_MS', '2000')),
            reconnection_delay_ms=int(os.getenv('TSLG_RECONNECTION_DELAY_MS', '2000')),
            socket_timeout_ms=int(os.getenv('TSLG_SOCKET_TIMEOUT_MS', '5000')),
            max_connection_attempts=int(os.getenv('TSLG_MAX_CONNECTION_ATTEMPTS', '10')),
            log_level=os.getenv('TSLG_LOG_LEVEL', 'info').upper(),
            console_output=os.getenv('TSLG_CONSOLE_OUTPUT', 'true').lower() == 'true'
        )


@dataclass
class AppLoggingConfig:
    """Конфигурация логирования приложения"""
    level: str
    logs_directory: Optional[Path]
    enable_file_logging: bool
    enable_console_logging: bool

    @classmethod
    def from_env(cls) -> 'AppLoggingConfig':
        logs_dir = Path(logs_directory) if logs_directory else None
        return cls(
            level=logging_level,
            logs_directory=logs_dir,
            enable_file_logging=bool(logs_directory),
            enable_console_logging=True
        )