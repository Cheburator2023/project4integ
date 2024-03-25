import json
import os
from typing import List, Dict, Optional


class Namespaces:
    _PREFIX = "namespace_"

    def __init__(self):
        self._items: dict = dict()
        self._repr = ''
        self._errors = []

    def __str__(self):
        return self._repr

    @property
    def items(self) -> Dict[str, List[str]]:
        return self._items

    @staticmethod
    def strint_to_list(s: str) -> List[str]:
        return list(set(s.replace(' ', '').replace("\n", "").split(',')))

    def _get_namespaces_from_env(self, startswith=_PREFIX) -> Dict[str, List[str]]:
        result = {}
        for namespace_key, value_string in os.environ.items():
            if namespace_key.startswith(startswith):
                key = namespace_key.split(startswith)[1]
                result[key] = self.strint_to_list(value_string)
        return result

    def get(self, name, default=None) -> Optional[str]:
        return self._items.get(name, default)

    def list_errors(self) -> List[str]:
        return self._errors

    def build_namespaces(self) -> None:
        ns_envs = self._get_namespaces_from_env()
        for client_id, ns_list in ns_envs.items():
            for ns_item in ns_list:
                if self._items.setdefault(ns_item, client_id) != client_id:
                    self._errors.append(f"Collision error {client_id} in namespace already with key {ns_item}")
        self._repr = json.dumps(self._items)


def get_namespace_map() -> Namespaces:
    namespaces: Namespaces = Namespaces()
    namespaces.build_namespaces()
    return namespaces
