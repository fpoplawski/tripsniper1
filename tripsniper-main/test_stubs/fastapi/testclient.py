from __future__ import annotations

def _unwrap_dep(dep):
    val = dep()
    if hasattr(val, "__next__"):
        return next(val)
    return val



import inspect
import json
from typing import Any, Callable, Dict

from . import Depends, Query


class Response:
    def __init__(self, data: Any, status_code: int = 200) -> None:
        self._data = data
        self.status_code = status_code

    def json(self) -> Any:
        return self._data


class TestClient:
    def __init__(self, app: Any) -> None:
        self.app = app

    def get(self, path: str, params: Dict[str, Any] | None = None) -> Response:
        params = params or {}
        handler = self.app.routes[path]
        sig = inspect.signature(handler)
        kwargs: Dict[str, Any] = {}
        for name, param in sig.parameters.items():
            default = param.default
            if isinstance(default, Query):
                kwargs[name] = params.get(name, default.default)
            elif isinstance(default, Depends):
                kwargs[name] = _unwrap_dep(default.dependency)
            else:
                kwargs[name] = params.get(name, default)
        result = handler(**kwargs)
        return Response(result)
