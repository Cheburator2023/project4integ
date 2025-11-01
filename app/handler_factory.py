import logging
import logging.config
from pathlib import Path
from typing import Dict, Any, List
from app.logging_config import AppLoggingConfig, TSLGConfig
from app.tslg_logging import TSLGJSONLogFormatter, TSLGBufferedSocketHandler


class LogHandlerFactory:
    """Фабрика для создания обработчиков логов"""

    @staticmethod
    def create_console_handler(formatter: logging.Formatter) -> logging.StreamHandler:
        """Создает консольный обработчик"""
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        return handler

    @staticmethod
    def create_file_handler(
        log_file: Path,
        formatter: logging.Formatter
    ) -> logging.FileHandler:
        """Создает файловый обработчик"""
        log_file.parent.mkdir(parents=True, exist_ok=True)

        handler = logging.FileHandler(str(log_file))
        handler.setFormatter(formatter)
        return handler

    @staticmethod
    def create_tslg_handler(
        config: TSLGConfig,
        formatter: TSLGJSONLogFormatter
    ) -> TSLGBufferedSocketHandler:
        """Создает TSLG обработчик"""
        handler = TSLGBufferedSocketHandler(
            host=config.host,
            port=config.port,
            max_buffer_size=config.max_buffer_size,
            flush_interval_ms=config.flush_interval_ms,
            connection_ttl_ms=config.connection_ttl_ms,
            reconnection_delay_ms=config.reconnection_delay_ms,
            socket_timeout_ms=config.socket_timeout_ms,
            max_connection_attempts=config.max_connection_attempts
        )
        handler.setLevel(getattr(logging, config.log_level, logging.INFO))
        handler.setFormatter(formatter)
        return handler

    @staticmethod
    def create_standard_formatter() -> logging.Formatter:
        """Создает стандартный форматтер"""
        return logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )

    @staticmethod
    def create_tslg_formatter() -> TSLGJSONLogFormatter:
        """Создает TSLG форматтер"""
        return TSLGJSONLogFormatter()