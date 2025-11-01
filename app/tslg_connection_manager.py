import socket
import threading
import time
import logging
from typing import Callable, Optional
from app.logging_config import TSLGConfig


class TSLGConnectionManager:
    """Управляет подключением к TSLG агенту и отслеживает его состояние"""

    def __init__(self, config: TSLGConfig):
        self.config = config
        self._is_healthy = False
        self._lock = threading.Lock()
        self._listeners = []
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_monitoring = False
        self.logger = logging.getLogger(__name__)

    def add_health_listener(self, listener: Callable[[bool], None]):
        """Добавляет слушателя изменений состояния подключения"""
        self._listeners.append(listener)

    def _notify_listeners(self, is_healthy: bool):
        """Уведомляет всех слушателей об изменении состояния"""
        for listener in self._listeners:
            try:
                listener(is_healthy)
            except Exception as e:
                self.logger.error(f"Error in health listener: {e}")

    def check_connection(self) -> bool:
        """Проверяет доступность TSLG агента"""
        try:
            with socket.create_connection(
                (self.config.host, self.config.port),
                timeout=5
            ):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False

    def start_health_monitoring(self):
        """Запускает мониторинг здоровья подключения"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return

        self._stop_monitoring = False
        self._monitor_thread = threading.Thread(
            target=self._health_monitor_worker,
            daemon=True,
            name="TSLGHealthMonitor"
        )
        self._monitor_thread.start()
        self.logger.info("TSLG health monitoring started")

    def stop_health_monitoring(self):
        """Останавливает мониторинг здоровья"""
        self._stop_monitoring = True
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)

    def _health_monitor_worker(self):
        """Фоновая задача для мониторинга здоровья подключения"""
        consecutive_failures = 0
        max_consecutive_failures = 3

        while not self._stop_monitoring:
            try:
                is_healthy = self.check_connection()

                with self._lock:
                    old_health = self._is_healthy
                    self._is_healthy = is_healthy

                    if old_health != is_healthy:
                        if is_healthy:
                            self.logger.info("TSLG connection established")
                            consecutive_failures = 0
                        else:
                            self.logger.warning("TSLG connection lost")
                        self._notify_listeners(is_healthy)

                if not is_healthy:
                    consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        self.logger.error(
                            f"TSLG connection failed {consecutive_failures} consecutive times"
                        )

            except Exception as e:
                self.logger.error(f"Error in health monitor: {e}")

            time.sleep(30)

    @property
    def is_healthy(self) -> bool:
        """Текущее состояние подключения"""
        with self._lock:
            return self._is_healthy

    def __enter__(self):
        self.start_health_monitoring()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_health_monitoring()