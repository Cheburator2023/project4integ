import logging
import logging.config
import threading
from typing import Dict, Any, List
from app.logging_config import AppLoggingConfig, TSLGConfig
from app.handler_factory import LogHandlerFactory
from app.tslg_connection_manager import TSLGConnectionManager


class LoggingManager:
    """Управляет всей конфигурацией логирования приложения"""

    def __init__(
        self,
        app_config: AppLoggingConfig,
        tslg_config: TSLGConfig
    ):
        self.app_config = app_config
        self.tslg_config = tslg_config
        self.connection_manager = TSLGConnectionManager(tslg_config)
        self.handler_factory = LogHandlerFactory()
        self._console_handler = None
        self._tslg_handler = None
        self._file_handler = None
        self._lock = threading.Lock()
        self.logger = logging.getLogger(__name__)

        self.connection_manager.add_health_listener(self._on_tslg_health_changed)

    def setup_logging(self) -> logging.Logger:
        """Настраивает логирование приложения"""
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.app_config.level, logging.INFO))

        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        self._create_handlers(root_logger)

        self._configure_logging_strategy(root_logger)

        self.connection_manager.start_health_monitoring()

        return root_logger

    def _create_handlers(self, root_logger: logging.Logger):
        """Создает все необходимые обработчики"""
        standard_formatter = self.handler_factory.create_standard_formatter()
        tslg_formatter = self.handler_factory.create_tslg_formatter()

        self._console_handler = self.handler_factory.create_console_handler(
            standard_formatter
        )

        if self.app_config.enable_file_logging:
            log_file = self.app_config.logs_directory / "integration.log"
            self._file_handler = self.handler_factory.create_file_handler(
                log_file, standard_formatter
            )
            root_logger.addHandler(self._file_handler)
            self.logger.info(f"File logging enabled: {log_file}")

        self._tslg_handler = self.handler_factory.create_tslg_handler(
            self.tslg_config, tslg_formatter
        )

    def _configure_logging_strategy(self, root_logger: logging.Logger):
        """Настраивает стратегию логирования на основе конфигурации"""

        if self.tslg_config.console_output:
            root_logger.addHandler(self._console_handler)
            root_logger.addHandler(self._tslg_handler)
            self.logger.info("TSLG console output enabled - logs sent to both TSLG and console")

        else:
            if self.connection_manager.is_healthy:
                root_logger.addHandler(self._tslg_handler)
                self.logger.info("TSLG connection established - using TSLG only")
            else:
                root_logger.addHandler(self._console_handler)
                root_logger.addHandler(self._tslg_handler)  # Все равно пробуем отправлять в TSLG
                self.logger.warning("TSLG unavailable - using console as fallback")

    def _on_tslg_health_changed(self, is_healthy: bool):
        """Обрабатывает изменения состояния подключения TSLG"""
        with self._lock:
            root_logger = logging.getLogger()

            if self.tslg_config.console_output:
                return

            if is_healthy:
                self._remove_console_handler(root_logger)
                self.logger.info("TSLG connection restored - disabled console output")
            else:
                self._add_console_handler(root_logger)
                self.logger.warning("TSLG connection lost - enabled console output")

    def _remove_console_handler(self, root_logger: logging.Logger):
        """Удаляет консольный обработчик"""
        if self._console_handler in root_logger.handlers:
            root_logger.removeHandler(self._console_handler)

    def _add_console_handler(self, root_logger: logging.Logger):
        """Добавляет консольный обработчик"""
        if self._console_handler not in root_logger.handlers:
            root_logger.addHandler(self._console_handler)

    def shutdown(self):
        """Корректно останавливает менеджер логирования"""
        self.connection_manager.stop_health_monitoring()

        if self._tslg_handler:
            self._tslg_handler.close()

        self.logger.info("Logging manager shutdown complete")


class LoggingManagerFactory:
    """Фабрика для создания менеджера логирования"""

    @staticmethod
    def create_from_env() -> LoggingManager:
        """Создает менеджер логирования из переменных окружения"""
        app_config = AppLoggingConfig.from_env()
        tslg_config = TSLGConfig.from_env()

        return LoggingManager(app_config, tslg_config)