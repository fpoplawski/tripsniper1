from __future__ import annotations

import inspect
from typing import Any, Callable, Dict

__all__ = ["FastAPI", "Query", "Depends", "Request"]


class Query:
    def __init__(self, default: Any = None, **kwargs: Any) -> None:
        self.default = default


class Depends:
    def __init__(self, dependency: Callable[..., Any]):
        self.dependency = dependency


class Request:
    def __init__(self, method: str = "", url: str = "") -> None:
        self.method = method
        self.url = url


class FastAPI:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.routes: Dict[str, Callable[..., Any]] = {}

    def add_middleware(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover
        pass

    def get(self, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.routes[path] = func
            return func

        return decorator

    def middleware(self, _type: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:  # pragma: no cover
            return func

        return decorator
