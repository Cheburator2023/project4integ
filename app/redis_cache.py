from enum import Enum
from functools import lru_cache
from json import dumps
from typing import Any, Dict, List, Optional, Tuple, Union, Callable
import logging

from redis import ConnectionError, ConnectionPool
from redis import Redis as RedisClient

from app import app
from app.config import (
    kafka_message_ttl,
    redis_healhcheck_interval,
    redis_host,
    redis_port,
    redis_username,
    redis_password,
)
from app.utils import decode_bytes, calc_hexdigest


@lru_cache(1)
def get_client(redis_db: int = 0) -> RedisClient:
    pool: ConnectionPool = ConnectionPool(
        host=redis_host, port=redis_port, db=redis_db, username=redis_username, password=redis_password
    )
    client: RedisClient = RedisClient(
        connection_pool=pool, health_check_interval=redis_healhcheck_interval
    )
    return client


class CacheStatus(Enum):
    Ok: str = "ok"
    ValidationError: str = "validation error"
    ServiceUnavailable: str = "target service unavailable"
    ResentManually: str = "resent manually"
    Blocked: str = "blocked for editing"
    UnexpectedError: str = "unexpected error"


def standard_hash_rule(data) -> str:
    if not data:
        return ""
    if isinstance(data, dict):
        data = dumps(data, sort_keys=True)
    return calc_hexdigest(data)


class Cache(object):
    def __init__(
            self,
            message_prefix: str = "",
            data: Union[str, Dict[Any, Any]] = "",
            redis_db: int = 7,
            hash_rule: Callable = None,
    ) -> None:
        try:
            self.redis_client: RedisClient = get_client(redis_db)
        except ConnectionError as err:
            logging.warning(f"Error connecting to redis server. {err}")
        if hash_rule:
            self.hash_rule = hash_rule
        else:
            self.hash_rule = standard_hash_rule
        self.hash_str: str = self.hash_rule(data)
        self.data: str = self.dumps_rule(data)
        self.status: CacheStatus = CacheStatus.Ok
        self.message_prefix: str = message_prefix

    @staticmethod
    def dumps_rule(data):
        # if data is dict convert it to string
        if isinstance(data, dict):
            data = dumps(data, sort_keys=True)
        return data

    def _list_all_keys(self) -> List[Tuple[str, str]]:
        return list({
            (i[0], i[1])
            for i in [
                j.decode("utf-8").split(":")
                for j in self.redis_client.keys(f"*:*")
            ]
        })

    def save_cache(self, status: CacheStatus, ttl=None) -> None:
        try:
            self.redis_client.set(
                f"{self.message_prefix}:{self.hash_str}",
                self.data,
                ex=ttl if ttl else kafka_message_ttl,
            )
            self.redis_client.set(
                f"{self.message_prefix}:{self.hash_str}:status",
                status.value,
                ex=ttl if ttl else kafka_message_ttl,
            )
        except ConnectionError as err:
            logging.warning(f"Error saving cache in redis. {err}")

    def get_by_data(self) -> Tuple[Optional[str], Optional[CacheStatus]]:
        cache: Optional[str] = None
        status: Optional[CacheStatus] = None
        try:
            cache = decode_bytes(
                self.redis_client.get(f"{self.message_prefix}:{self.hash_str}")
            )
            if cache is not None:
                status = decode_bytes(
                    self.redis_client.get(
                        f"{self.message_prefix}:{self.hash_str}:status"
                    )
                )
        except ConnectionError as err:
            logging.warning(
                f"Error getting cache by data, error connecting "
                f"to redis server. {err}"
            )
        return cache, status

    def get_by_id(self, cache_id: str) -> Optional[str]:
        cache: Optional[str] = None
        try:
            cache = decode_bytes(
                self.redis_client.get(f"{self.message_prefix}:{cache_id}")
            )
            if cache is not None:
                self.data = cache
        except ConnectionError as err:
            logging.warning(
                f"An error occurred while getting the cache by message id. "
                f"Error connecting to redis server. {err}"
            )
        return cache

    def get_all(self) -> List[Dict[str, Optional[str]]]:
        result: List[Dict[str, Optional[str]]] = []
        try:
            keys: List[Tuple[str, str]] = self._list_all_keys()
            for prefix, key in keys:
                cache: Optional[str] = decode_bytes(
                    self.redis_client.get(f"{prefix}:{key}")
                )
                status: Optional[str] = decode_bytes(
                    self.redis_client.get(
                        f"{prefix}:{key}:status"
                    )
                )
                result.append({"key": key, "status": status, "cache": cache})
        except ConnectionError as err:
            logging.warning(
                f"Error getting all cache entries. Error connecting to redis "
                f"server. {err}"
            )
        return result

    def delete_by_id(self, cache_id: str, prefix: str = "") -> bool:
        try:
            if not prefix:
                prefix = {
                    k.decode("utf-8").split(":")[0] for k in
                    self.redis_client.keys(f"*:{cache_id}")
                }.pop()
            deletion_result: int = self.redis_client.delete(
                f"{prefix}:{cache_id}",
            )
            if not deletion_result:
                raise KeyError
            self.redis_client.delete(
                f"{prefix}:{cache_id}:status"
            )
        except ConnectionError as err:
            logging.warning(
                f"Error while trying to delete cache entry by id '{cache_id}'."
                f"Error connecting to redis server. {err}"
            )
            return False
        except KeyError:
            logging.warning(
                f"Error while trying to delete cache entry. The entry "
                f"with id '{cache_id}' was not found in the cache."
            )
            return False
        return True

    def delete_all(self) -> bool:
        try:
            keys: List[Tuple[str, str]] = self._list_all_keys()
        except ConnectionError as err:
            logging.warning(
                f"Cache invalidation error. Error connecting to redis "
                f"server. {err}"
            )
            return False
        for prefix, key in keys:
            result: bool = self.delete_by_id(key, prefix)
            if not result:
                return result
        return True
