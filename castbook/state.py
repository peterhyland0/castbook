"""Shared run state: characters, runs, idempotency keys, cancel flags.

Production would put this in Postgres (the plan's step table). Here it's a
key-value interface with two backends: an in-memory dict for tests and a
modal.Dict for deployments, which the API container and the orchestrator
container can both see without a database. The interface is small on purpose
so swapping in Postgres later touches one file.
"""

import threading
from typing import Any, Protocol


class StateStore(Protocol):
    def get(self, namespace: str, key: str) -> Any | None: ...
    def put(self, namespace: str, key: str, value: Any) -> None: ...
    def keys(self, namespace: str) -> list[str]: ...


class MemoryState:
    def __init__(self):
        self._d: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def get(self, namespace, key):
        with self._lock:
            return self._d.get(namespace, {}).get(key)

    def put(self, namespace, key, value):
        with self._lock:
            self._d.setdefault(namespace, {})[key] = value

    def keys(self, namespace):
        with self._lock:
            return list(self._d.get(namespace, {}))


class ModalDictState:
    """One modal.Dict per namespace (`castbook-<namespace>`)."""

    def __init__(self, prefix: str = "castbook"):
        self.prefix = prefix
        self._dicts: dict[str, Any] = {}

    def _dict(self, namespace: str):
        if namespace not in self._dicts:
            import modal

            self._dicts[namespace] = modal.Dict.from_name(f"{self.prefix}-{namespace}", create_if_missing=True)
        return self._dicts[namespace]

    def get(self, namespace, key):
        return self._dict(namespace).get(key)

    def put(self, namespace, key, value):
        self._dict(namespace)[key] = value

    def keys(self, namespace):
        return list(self._dict(namespace).keys())
