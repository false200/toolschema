from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, TypeVar, overload

from toolschema._introspect import ToolMeta

F = TypeVar("F", bound=Callable[..., Any])


@overload
def tool(fn: F) -> F: ...


@overload
def tool(
    *,
    name: str | None = None,
    description: str | None = None,
) -> Callable[[F], F]: ...


def tool(
    fn: F | None = None,
    *,
    name: str | None = None,
    description: str | None = None,
) -> F | Callable[[F], F]:
    """Mark a function as a tool and optionally override name or description."""

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        wrapper._toolschema = ToolMeta(  # type: ignore[attr-defined]
            name=name,
            description=description,
        )
        wrapper.__wrapped__ = func  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    if fn is not None:
        return decorator(fn)
    return decorator
